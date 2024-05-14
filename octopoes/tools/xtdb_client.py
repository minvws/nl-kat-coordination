import datetime
from typing import Any

import httpx


class XTDBClient:
    def __init__(self, base_url: str, node: str, timeout: int | None = None):
        self._client = httpx.Client(
            base_url=f"{base_url}/_xtdb/{node}",
            headers={"Accept": "application/json"},
            timeout=timeout,
        )

    def status(self) -> Any:
        res = self._client.get("/status")

        return res.text

    def query(self, query: str = "{:query {:find [ ?var ] :where [[?var :xt/id ]]}}") -> Any:
        res = self._client.post("/query", content=query, headers={"Content-Type": "application/edn"})

        return res.text

    def entity(
        self,
        key: str,
        valid_time: datetime.datetime | None = None,
        tx_time: datetime.datetime | None = None,
        tx_id: int | None = None,
    ) -> Any:
        params = {"eid": key}
        if valid_time is not None:
            params["valid-time"] = valid_time.isoformat()
        if tx_time is not None:
            params["tx-time"] = tx_time.isoformat()
        if tx_id is not None:
            params["tx-id"] = str(tx_id)

        res = self._client.get("/entity", params=params)

        return res.text

    def history(self, key: str, with_corrections: bool, with_docs: bool) -> Any:
        params = {"eid": key, "history": True, "sortOrder": "asc"}
        if with_corrections:
            params["with-corrections"] = "true"
        if with_docs:
            params["with-docs"] = "true"

        res = self._client.get("/entity", params=params)

        return res.text

    def entity_tx(
        self,
        key: str,
        valid_time: datetime.datetime | None = None,
        tx_time: datetime.datetime | None = None,
        tx_id: int | None = None,
    ) -> Any:
        params = {"eid": key}
        if valid_time is not None:
            params["valid-time"] = valid_time.isoformat()
        if tx_time is not None:
            params["tx-time"] = tx_time.isoformat()
        if tx_id is not None:
            params["tx-id"] = str(tx_id)
        res = self._client.get("/entity-tx", params=params)

        return res.text

    def attribute_stats(self) -> Any:
        res = self._client.get("/attribute-stats")

        return res.text

    def sync(self, timeout: int | None) -> Any:
        if timeout is not None:
            res = self._client.get("/sync", params={"timeout": timeout})
        else:
            res = self._client.get("/sync")

        return res.text

    def await_tx(self, transaction_id: int, timeout: int | None) -> Any:
        params = {"txId": transaction_id}
        if timeout is not None:
            params["timeout"] = timeout
        res = self._client.get("/await-tx", params=params)

        return res.text

    def await_tx_time(
        self,
        transaction_time: datetime.datetime,
        timeout: int | None,
    ) -> Any:
        params = {"tx-time": transaction_time.isoformat()}
        if timeout is not None:
            params["timeout"] = str(timeout)
        res = self._client.get("/await-tx-time", params=params)

        return res.text

    def tx_log(
        self,
        after_tx_id: int | None,
        with_ops: bool,
    ) -> Any:
        params = {}
        if after_tx_id is not None:
            params["after-tx-id"] = str(after_tx_id)
        if with_ops:
            params["with-ops?"] = "true"

        res = self._client.get("/tx-log", params=params)

        return res.text

    def submit_tx(self, transactions: list[str]) -> Any:
        res = self._client.post("/submit-tx", json={"tx-ops": transactions})

        return res.text

    def tx_committed(self, txid: int) -> Any:
        res = self._client.get("/tx-committed", params={"txId": txid})

        return res.text

    def latest_completed_tx(self) -> Any:
        res = self._client.get("/latest-completed-tx")

        return res.text

    def latest_submitted_tx(self) -> Any:
        res = self._client.get("/latest-submitted-tx")

        return res.text

    def active_queries(self) -> Any:
        res = self._client.get("/active-queries")

        return res.text

    def recent_queries(self) -> Any:
        res = self._client.get("/recent-queries")
        return res.text

    def slowest_queries(self) -> Any:
        res = self._client.get("/recent-queries")
        return res.text
