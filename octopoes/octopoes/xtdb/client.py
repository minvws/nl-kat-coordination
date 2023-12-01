import logging
from datetime import datetime, timezone
from enum import Enum
from functools import lru_cache
from http import HTTPStatus
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union

import requests
from pydantic import BaseModel, Field, parse_obj_as
from requests import HTTPError, Response

from octopoes.models.transaction import TransactionRecord
from octopoes.xtdb.exceptions import NodeNotFound, NoMultinode, XTDBException
from octopoes.xtdb.query import Query

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
        self.headers["Accept"] = "application/json"

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


@lru_cache(maxsize=1)
def get_xtdb_http_session(base_url):
    return XTDBHTTPSession(base_url)


class XTDBHTTPClient:
    def __init__(self, base_url, client: str, multinode=False):
        self._client = client
        self._is_multinode = multinode
        self._session = get_xtdb_http_session(base_url)

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

    def client_url(self) -> str:
        if not self._is_multinode:
            return ""

        return f"/{self._client}"

    def status(self) -> XTDBStatus:
        res = self._session.get(f"{self.client_url()}/status")
        self._verify_response(res)
        return XTDBStatus.parse_obj(res.json())

    def get_entity(self, entity_id: str, valid_time: Optional[datetime] = None) -> dict:
        if valid_time is None:
            valid_time = datetime.now(timezone.utc)
        res = self._session.get(
            f"{self.client_url()}/entity", params={"eid": entity_id, "valid-time": valid_time.isoformat()}
        )
        self._verify_response(res)
        return res.json()

    def get_entity_history(
        self,
        entity_id: str,
        *,
        sort_order: str = "asc",  # Or: "desc"
        with_docs: bool = True,
        has_doc: Optional[bool] = None,
        offset: int = 0,
        limit: Optional[int] = None,
        indices: Optional[List[int]] = None,
    ) -> List[TransactionRecord]:
        params = {
            "eid": entity_id,
            "sort-order": sort_order,
            "history": "true",
            "with-docs": "true" if with_docs else "false",
        }

        res = self._session.get(f"{self.client_url()}/entity", params=params)
        self._verify_response(res)

        transactions: List[TransactionRecord] = parse_obj_as(List[TransactionRecord], res.json())
        if has_doc is True and with_docs is True:  # Checking makes no sense without docs
            transactions = [transaction for transaction in transactions if transaction.doc]

        if has_doc is False and with_docs is True:  # Checking makes no sense without docs
            transactions = [transaction for transaction in transactions if not transaction.doc]

        if indices:
            return [tx for i, tx in enumerate(transactions) if i in indices or i - len(transactions) in indices]

        return transactions[offset:limit]

    def query(self, query: Union[str, Query], valid_time: Optional[datetime] = None) -> List[List[Any]]:
        if valid_time is None:
            valid_time = datetime.now(timezone.utc)
        res = self._session.post(
            f"{self.client_url()}/query",
            params={"valid-time": valid_time.isoformat()},
            data=str(query),
            headers={"Content-Type": "application/edn"},
        )
        self._verify_response(res)
        return res.json()

    def await_transaction(self, transaction_id: int) -> None:
        self._session.get(f"{self.client_url()}/await-tx", params={"txId": transaction_id})
        logger.info("Transaction completed [txId=%s]", transaction_id)

    def submit_transaction(self, operations: List[Operation]) -> None:
        res = self._session.post(
            f"{self.client_url()}/submit-tx",
            data=Transaction(operations=operations).json(by_alias=True),
            headers={"Content-Type": "application/json"},
        )

        self._verify_response(res)
        self.await_transaction(res.json()["txId"])

    def create_node(self) -> None:
        if not self._is_multinode:
            raise NoMultinode("Creating nodes requires XTDB multinode")

        try:
            res = self._session.post("/create-node", json={"node": self._client})
            self._verify_response(res)
        except HTTPError as e:
            logger.exception("Failed creating node")
            raise XTDBException("Could not create node") from e

    def delete_node(self) -> None:
        if not self._is_multinode:
            raise NoMultinode("Deleting nodes requires XTDB multinode")

        try:
            res = self._session.post("/delete-node", json={"node": self._client})
            self._verify_response(res)
        except HTTPError as e:
            if e.response.status_code == HTTPStatus.NOT_FOUND:
                raise NodeNotFound from e

            logger.exception("Failed deleting node")

            raise XTDBException("Could not delete node") from e

    def sync(self, timeout: Optional[int] = None):
        params = {}

        if timeout is not None:
            params["timeout"] = timeout

        res = self._session.get(f"{self.client_url()}/sync", params=params)
        self._verify_response(res)

        return res.json()


class XTDBSession:
    def __init__(self, client: XTDBHTTPClient):
        self.client = client

        self._operations = []
        self.post_commit_callbacks = []

    def __enter__(self):
        return self

    def __exit__(self, _exc_type: Type[Exception], _exc_value: str, _exc_traceback: str) -> None:
        self.commit()

    def add(self, operation: Operation):
        self._operations.append(operation)

    def put(self, document: Union[str, Dict[str, Any]], valid_time: datetime):
        self.add((OperationType.PUT, document, valid_time))

    def commit(self) -> None:
        if self._operations:
            logger.debug(self._operations)
            self.client.submit_transaction(self._operations)
            self._operations = []

        if not self.post_commit_callbacks:
            return

        for callback in self.post_commit_callbacks:
            callback()

        logger.info("Called %s callbacks after committing XTDBSession", len(self.post_commit_callbacks))
        self.post_commit_callbacks = []

    def listen_post_commit(self, callback: Callable[[], None]):
        self.post_commit_callbacks.append(callback)
