import logging
from datetime import timezone, datetime
from enum import Enum
from http import HTTPStatus
from typing import Union, Optional, Tuple, List, Dict, Any, Type, Callable

import requests
from pydantic import BaseModel, Field
from requests import Response, HTTPError

logger = logging.getLogger(__name__)


class OperationType(Enum):
    PUT = "put"
    DELETE = "delete"
    MATCH = "match"
    EVICT = "evict"
    FN = "fn"


Operation = Tuple[OperationType, Union[str, Dict[str, Any]], Optional[datetime]]


class Transaction(BaseModel):
    operations: List[Operation] = Field(alias="tx-ops")

    class Config:
        allow_population_by_field_name = True


class XTDBHTTPSession(requests.Session):
    def __init__(self, base_url: str):
        super().__init__()

        self._base_url = base_url
        self.headers["Accept"] = f"application/json"

    def request(self, method: str, url: Union[str, bytes], **kwargs) -> requests.Response:
        return super().request(method, self._base_url + str(url), **kwargs)


class XTDBStatus(BaseModel):
    version: Optional[str]
    revision: Optional[str]
    indexVersion: Optional[int]
    consumerState: Optional[str]
    kvStore: Optional[str]
    estimateNumKeys: Optional[int]
    size: Optional[int]


class XTDBHTTPClient:
    def __init__(self, base_url):
        self._session = XTDBHTTPSession(base_url)

    @staticmethod
    def _verify_response(response: Response) -> None:
        try:
            response.raise_for_status()
        except HTTPError as e:
            if e.response.status_code != HTTPStatus.NOT_FOUND:
                logger.error(response.request.url)
                logger.error(response.request.body)
                logger.error(response.text)
            raise e

    def status(self) -> XTDBStatus:
        res = self._session.get("/status")
        self._verify_response(res)
        return XTDBStatus.parse_obj(res.json())

    def get_entity(self, entity_id: str, valid_time: Optional[datetime] = None) -> dict:
        if valid_time is None:
            valid_time = datetime.now(timezone.utc)
        res = self._session.get("/entity", params={"eid": entity_id, "valid-time": valid_time.isoformat()})
        self._verify_response(res)
        return res.json()

    def query(self, query: str, valid_time: Optional[datetime] = None) -> Dict:
        if valid_time is None:
            valid_time = datetime.now(timezone.utc)
        res = self._session.post(
            "/query",
            params={"valid-time": valid_time.isoformat()},
            data=query,
            headers={"Content-Type": "application/edn"},
        )
        self._verify_response(res)
        return res.json()

    def await_transaction(self, transaction_id: int) -> None:
        logger.debug(f"Awaiting transaction {transaction_id}")
        self._session.get(f"/await-tx", params={"txId": transaction_id})
        logger.debug(f"Transaction {transaction_id} done")

    def submit_transaction(self, operations: List[Operation]) -> None:
        res = self._session.post(
            "/submit-tx",
            data=Transaction(operations=operations).json(by_alias=True),
            headers={"Content-Type": "application/json"},
        )

        self._verify_response(res)
        self.await_transaction(res.json()["txId"])


class XTDBSession:
    def __init__(self, client: XTDBHTTPClient):
        self.client = client

        self._operations = []
        self._committed = False
        self.post_commit_callbacks = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type: Type[Exception], exc_value: str, exc_traceback: str) -> None:
        self.commit()

    def add(self, operation: Operation):
        self._operations.append(operation)

    def commit(self):
        if self._committed:
            raise RuntimeError("Session already committed")

        logger.debug("commiting session")

        if self._operations:
            logger.debug(self._operations)
            self.client.submit_transaction(self._operations)

        self._committed = True

        for callback in self.post_commit_callbacks:
            callback()

    def listen_post_commit(self, callback: Callable[[], None]):
        self.post_commit_callbacks.append(callback)
