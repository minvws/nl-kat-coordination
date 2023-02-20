"""XTDB HTTP client."""

from __future__ import annotations

import logging
from datetime import timezone, datetime
from enum import Enum
from http import HTTPStatus
from typing import Union, Optional, Tuple, List, Dict, Any, Type, Callable, cast

import requests
from pydantic import BaseModel, Field
from requests import Response, HTTPError

logger = logging.getLogger(__name__)


class OperationType(Enum):
    """Operation types for XTDB transactions."""

    PUT = "put"
    DELETE = "delete"
    MATCH = "match"
    EVICT = "evict"
    FN = "fn"


Operation = Tuple[OperationType, Union[str, Dict[str, Any]], Optional[datetime]]


class Transaction(BaseModel):
    """A XTDB transaction, consisting of a list of operations."""

    operations: List[Operation] = Field(alias="tx-ops")

    class Config:
        """Serialize operations as 'tx-ops' in JSON."""

        allow_population_by_field_name = True


class XTDBHTTPSession(requests.Session):
    """A requests session that adds the base URL to all requests."""

    def __init__(self, base_url: str):
        """Initialize instance."""
        super().__init__()

        self._base_url = base_url
        self.headers["Accept"] = "application/json"

    def request(self, method: str, url: Union[str, bytes], **kwargs) -> requests.Response:  # type: ignore
        """Execute request with prepended base URL."""
        return super().request(method, self._base_url + str(url), **kwargs)


class XTDBStatus(BaseModel):
    """Status response from XTDB."""

    version: Optional[str]
    revision: Optional[str]
    index_version: Optional[int] = Field(None, alias="indexVersion")
    consumer_state: Optional[str] = Field(None, alias="consumerState")
    kv_store: Optional[str] = Field(None, alias="kvStore")
    estimate_num_keys: Optional[int] = Field(None, alias="estimateNumKeys")
    size: Optional[int]


class XTDBHTTPClient:
    """A HTTP client for XTDB."""

    def __init__(self, base_url: str) -> None:
        """Initialize instance."""
        self._session = XTDBHTTPSession(base_url)

    @staticmethod
    def _verify_response(response: Response) -> None:
        """Log upon invalid request."""
        try:
            response.raise_for_status()
        except HTTPError as exc:
            if exc.response.status_code != HTTPStatus.NOT_FOUND:
                logger.error(response.request.url)
                logger.error(response.request.body)
                logger.error(response.text)
            raise exc

    def status(self) -> XTDBStatus:
        """Get XTDB status."""
        res = self._session.get("/status")
        self._verify_response(res)
        return XTDBStatus.parse_raw(res.content)

    def get_entity(self, entity_id: str, valid_time: Optional[datetime] = None) -> Dict[str, Any]:
        """Load entity from XTDB."""
        if valid_time is None:
            valid_time = datetime.now(timezone.utc)
        res = self._session.get("/entity", params={"eid": entity_id, "valid-time": valid_time.isoformat()})
        self._verify_response(res)
        return cast(Dict[str, Any], res.json())

    def query(self, query: str, valid_time: Optional[datetime] = None) -> Any:
        """Query XTDB."""
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
        """Wait for transaction to complete."""
        self._session.get("/await-tx", params={"txId": transaction_id})
        logger.info("Transaction completed [txId=%s]", transaction_id)

    def submit_transaction(self, operations: List[Operation]) -> None:
        """Submit transaction to XTDB."""
        res = self._session.post(
            "/submit-tx",
            data=Transaction(operations=operations).json(by_alias=True),
            headers={"Content-Type": "application/json"},
        )

        self._verify_response(res)
        self.await_transaction(res.json()["txId"])

    def create_node(self, name: str) -> None:
        """Create node in XTDB-multinode."""
        res = self._session.post("/create-node", json={"node": name})

        self._verify_response(res)

    def delete_node(self, name: str) -> None:
        """Delete node in XTDB-multinode."""
        res = self._session.post(
            "/delete-node",
            json={"node": name},
        )

        self._verify_response(res)


class XTDBSession:
    """Session to collect XTDB operations and commit them in a single transaction."""

    def __init__(self, client: XTDBHTTPClient):
        """Initialize instance."""
        self.client = client

        self._operations: List[Operation] = []
        self._committed = False
        self.post_commit_callbacks: List[Callable[..., Any]] = []

    def __enter__(self) -> XTDBSession:
        """Enter context manager."""
        return self

    def __exit__(self, _exc_type: Type[Exception], _exc_value: str, _exc_traceback: str) -> None:
        """Exit context manager."""
        self.commit()

    def add(self, operation: Operation) -> None:
        """Add operation to session."""
        self._operations.append(operation)

    def commit(self) -> None:
        """Commit session."""
        if self._committed:
            raise RuntimeError("Session already committed")

        if self._operations:
            logger.debug(self._operations)
            self.client.submit_transaction(self._operations)

        self._committed = True

        for callback in self.post_commit_callbacks:
            callback()

    def listen_post_commit(self, callback: Callable[..., None]) -> None:
        """Register callback to be called after commit."""
        self.post_commit_callbacks.append(callback)
