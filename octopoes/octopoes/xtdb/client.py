import functools
from collections.abc import Callable
from datetime import datetime, timezone
from enum import Enum
from json import JSONDecodeError
from typing import Any

import httpx
import structlog
from httpx import HTTPError, HTTPStatusError, Response, codes
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from octopoes.models.transaction import TransactionRecord
from octopoes.xtdb.exceptions import NodeNotFound, XTDBException
from octopoes.xtdb.query import Query

logger = structlog.get_logger(__name__)


class OperationType(Enum):
    PUT = "put"
    DELETE = "delete"
    MATCH = "match"
    EVICT = "evict"
    FN = "fn"


Operation = tuple[OperationType, str | dict[str, Any], datetime | None]


class Transaction(BaseModel):
    operations: list[Operation] = Field(alias="tx-ops")
    model_config = ConfigDict(populate_by_name=True)


class XTDBStatus(BaseModel):
    version: str | None = None
    revision: str | None = None
    indexVersion: int | None = None
    consumerState: str | None = None
    kvStore: str | None = None
    estimateNumKeys: int | None = None
    size: int | None = None


@functools.cache
def _get_xtdb_http_session(base_url: str) -> httpx.Client:
    return httpx.Client(
        base_url=base_url, headers={"Accept": "application/json"}, transport=(httpx.HTTPTransport(retries=3))
    )


class XTDBHTTPClient:
    def __init__(self, base_url, client: str):
        self._client = client
        self._session = _get_xtdb_http_session(base_url)

    @staticmethod
    def _verify_response(response: Response) -> None:
        try:
            response.raise_for_status()
        except HTTPStatusError as e:
            try:
                if response.json()["error"] == "Node not found":
                    raise NodeNotFound() from e
            except (KeyError, JSONDecodeError):
                pass
            raise e

    def client_url(self) -> str:
        return f"/{self._client}"

    def status(self) -> XTDBStatus:
        res = self._session.get(f"{self.client_url()}/status")
        self._verify_response(res)
        return XTDBStatus.model_validate_json(res.content)

    def get_entity(self, entity_id: str, valid_time: datetime | None = None) -> dict:
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
        with_docs: bool = False,
        has_doc: bool | None = None,
        offset: int = 0,
        limit: int | None = None,
        indices: list[int] | None = None,
    ) -> list[TransactionRecord]:
        params = {
            "eid": entity_id,
            "sort-order": sort_order,
            "history": "true",
            "with-docs": "true" if with_docs else "false",
        }

        res = self._session.get(f"{self.client_url()}/entity", params=params)
        self._verify_response(res)
        transactions: list[TransactionRecord] = TypeAdapter(list[TransactionRecord]).validate_json(res.content)

        if has_doc is True:  # The doc is None if and only if the hash is  "0000000000000000000000000000000000000000"
            transactions = [transaction for transaction in transactions if transaction.content_hash != 40 * "0"]

        if has_doc is False:  # The doc is None if and only if the hash is  "0000000000000000000000000000000000000000"
            transactions = [transaction for transaction in transactions if transaction.content_hash == 40 * "0"]

        if indices:
            return [tx for i, tx in enumerate(transactions) if i in indices or i - len(transactions) in indices]

        return transactions[offset:limit]

    def query(self, query: str | Query, valid_time: datetime | None = None) -> list[list[Any]]:
        if valid_time is None:
            valid_time = datetime.now(timezone.utc)
        res = self._session.post(
            f"{self.client_url()}/query",
            params={"valid-time": valid_time.isoformat()},
            content=" ".join(str(query).split()),
            headers={"Content-Type": "application/edn"},
        )
        self._verify_response(res)
        return res.json()

    def await_transaction(self, transaction_id: int) -> None:
        self._session.get(f"{self.client_url()}/await-tx", params={"txId": transaction_id})
        logger.info("Transaction completed [txId=%s]", transaction_id)

    def submit_transaction(self, operations: list[Operation]) -> None:
        res = self._session.post(
            f"{self.client_url()}/submit-tx",
            content=Transaction(operations=operations).json(by_alias=True),
            headers={"Content-Type": "application/json"},
        )

        self._verify_response(res)
        self.await_transaction(res.json()["txId"])

    def create_node(self) -> None:
        try:
            res = self._session.post("/create-node", json={"node": self._client})
            self._verify_response(res)
        except HTTPError as e:
            logger.exception("Failed creating node")
            raise XTDBException("Could not create node") from e

    def delete_node(self) -> None:
        try:
            res = self._session.post("/delete-node", json={"node": self._client})
            self._verify_response(res)
        except HTTPError as e:
            if isinstance(e, HTTPStatusError) and e.response.status_code == codes.NOT_FOUND:
                raise NodeNotFound from e

            logger.exception("Failed deleting node")

            raise XTDBException("Could not delete node") from e

    def export_transactions(self):
        res = self._session.get(f"{self.client_url()}/tx-log?with-ops?=true", headers={"Accept": "application/json"})
        self._verify_response(res)
        return res.json()

    def sync(self, timeout: int | None = None):
        params = {}

        if timeout is not None:
            params["timeout"] = timeout

        res = self._session.get(f"{self.client_url()}/sync", params=params)
        self._verify_response(res)

        return res.json()


class XTDBSession:
    def __init__(self, client: XTDBHTTPClient):
        self.client = client

        self._operations: list[Operation] = []
        self.post_commit_callbacks: list[Callable[[], None]] = []

    def __enter__(self):
        return self

    def __exit__(self, _exc_type: type[Exception], _exc_value: str, _exc_traceback: str) -> None:
        self.commit()

    def add(self, operation: Operation):
        self._operations.append(operation)

    def put(self, document: str | dict[str, Any], valid_time: datetime):
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
