import datetime

import httpx
from pydantic import JsonValue

PutTransaction = (
    tuple[str, dict]
    | tuple[str, dict, str | datetime.datetime]
    | tuple[str, dict, str | datetime.datetime, str | datetime.datetime]
)

DeleteTransaction = (
    tuple[str] | tuple[str, str | datetime.datetime] | tuple[str, str | datetime.datetime, str | datetime.datetime]
)

EvictTransaction = DeleteTransaction

SimpleTransactions = list[PutTransaction | DeleteTransaction | EvictTransaction]

MatchTransaction = (
    tuple[str, str, dict, SimpleTransactions] | tuple[str, str, dict, str | datetime.datetime, SimpleTransactions]
)

TransactionType = PutTransaction | DeleteTransaction | EvictTransaction | MatchTransaction


class XTDBClient:
    def __init__(self, base_url: str, node: str, timeout: int | None = None):
        self._client = httpx.Client(
            base_url=f"{base_url}/_xtdb/{node}",
            headers={"Accept": "application/json"},
            timeout=timeout,
        )

    def status(self) -> JsonValue:
        res = self._client.get("/status")

        return res.json()

    def query(
        self,
        query: str = "{:query {:find [ ?var ] :where [[?var :xt/id ]]}}",
        valid_time: datetime.datetime | None = None,
        tx_time: datetime.datetime | None = None,
        tx_id: int | None = None,
    ) -> JsonValue:
        params = {}
        if valid_time is not None:
            params["valid-time"] = valid_time.isoformat()
        if tx_time is not None:
            params["tx-time"] = tx_time.isoformat()
        if tx_id is not None:
            params["tx-id"] = str(tx_id)

        res = self._client.post("/query", params=params, content=query, headers={"Content-Type": "application/edn"})

        return res.json()

    def entity(
        self,
        key: str,
        valid_time: datetime.datetime | None = None,
        tx_time: datetime.datetime | None = None,
        tx_id: int | None = None,
    ) -> JsonValue:
        params = {"eid": key}
        if valid_time is not None:
            params["valid-time"] = valid_time.isoformat()
        if tx_time is not None:
            params["tx-time"] = tx_time.isoformat()
        if tx_id is not None:
            params["tx-id"] = str(tx_id)

        res = self._client.get("/entity", params=params)

        return res.json()

    def history(self, key: str, with_corrections: bool, with_docs: bool) -> JsonValue:
        params = {"eid": key, "history": True, "sortOrder": "asc"}
        if with_corrections:
            params["with-corrections"] = "true"
        if with_docs:
            params["with-docs"] = "true"

        res = self._client.get("/entity", params=params)

        return res.json()

    def entity_tx(
        self,
        key: str,
        valid_time: datetime.datetime | None = None,
        tx_time: datetime.datetime | None = None,
        tx_id: int | None = None,
    ) -> JsonValue:
        params = {"eid": key}
        if valid_time is not None:
            params["valid-time"] = valid_time.isoformat()
        if tx_time is not None:
            params["tx-time"] = tx_time.isoformat()
        if tx_id is not None:
            params["tx-id"] = str(tx_id)
        res = self._client.get("/entity-tx", params=params)

        return res.json()

    def attribute_stats(self) -> JsonValue:
        res = self._client.get("/attribute-stats")

        return res.json()

    def sync(self, timeout: int | None) -> JsonValue:
        if timeout is not None:
            res = self._client.get("/sync", params={"timeout": timeout})
        else:
            res = self._client.get("/sync")

        return res.json()

    def await_tx(self, transaction_id: int, timeout: int | None) -> JsonValue:
        params = {"txId": transaction_id}
        if timeout is not None:
            params["timeout"] = timeout
        res = self._client.get("/await-tx", params=params)

        return res.json()

    def await_tx_time(
        self,
        transaction_time: datetime.datetime,
        timeout: int | None,
    ) -> JsonValue:
        params = {"tx-time": transaction_time.isoformat()}
        if timeout is not None:
            params["timeout"] = str(timeout)
        res = self._client.get("/await-tx-time", params=params)

        return res.json()

    def tx_log(
        self,
        after_tx_id: int | None,
        with_ops: bool,
    ) -> JsonValue:
        params = {}
        if after_tx_id is not None:
            params["after-tx-id"] = after_tx_id
        if with_ops:
            params["with-ops?"] = True

        res = self._client.get("/tx-log", params=params)

        return res.json()

    def submit_tx(self, transactions: list[TransactionType]) -> JsonValue:
        data = {"tx-ops": transactions}
        res = self._client.post("/submit-tx", json=data)

        return res.json()

    def tx_committed(self, txid: int) -> JsonValue:
        res = self._client.get("/tx-committed", params={"txId": txid})

        return res.json()

    def latest_completed_tx(self) -> JsonValue:
        res = self._client.get("/latest-completed-tx")

        return res.json()

    def latest_submitted_tx(self) -> JsonValue:
        res = self._client.get("/latest-submitted-tx")

        return res.json()

    def active_queries(self) -> JsonValue:
        res = self._client.get("/active-queries")

        return res.json()

    def recent_queries(self) -> JsonValue:
        res = self._client.get("/recent-queries")

        return res.json()

    def slowest_queries(self) -> JsonValue:
        res = self._client.get("/recent-queries")

        return res.json()
