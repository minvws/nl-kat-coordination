#!/usr/bin/env python

import argparse
import datetime
import sys
from pathlib import Path
from typing import Any

import httpx
import click


class XTDBClient:
    def __init__(self, base_url: str, node: str, timeout: int | None = None):
        self._client = httpx.Client(
            base_url=f"{base_url}/_xtdb/{node}",
            headers={"Accept": "application/json"},
            timeout=timeout,
        )

    def status(self) -> Any:
        res = self._client.get("/status")

        return res.json()

    def query(
        self, query: str = "{:query {:find [ ?var ] :where [[?var :xt/id ]]}}"
    ) -> Any:
        res = self._client.post(
            "/query", content=query, headers={"Content-Type": "application/edn"}
        )

        return res.json()

    def entity(self, key: str):
        res = self._client.get(f"/entity", params={"eid": key})

        return res.json()

    def history(self, key: str) -> Any:
        res = self._client.get(
            f"/entity", params={"eid": key, "history": True, "sortOrder": "asc"}
        )

        return res.json()

    def entity_tx(self, key: str) -> Any:
        res = self._client.get(f"/entity-tx", params={"eid": key})

        return res.json()

    def attribute_stats(self) -> Any:
        res = self._client.get("/attribute-stats")

        return res.json()

    def sync(self, timeout: int = 500):
        headers = {"Accept": "application/json"}
        req = httpx.get(self._root(f"sync?timeout={timeout}"), headers=headers)
        return req.text

    def await_tx(self, txid: int):
        headers = {"Accept": "application/json"}
        req = httpx.get(self._root(f"await-tx?txId={txid}"), headers=headers)
        return req.text

    def await_tx_time(self, tm: str = datetime.datetime.now().isoformat()):
        headers = {"Accept": "application/json"}
        req = httpx.get(self._root(f"await-tx-time?tx-time={tm}"), headers=headers)
        return req.text

    def tx_log(self):
        headers = {"Accept": "application/json"}
        req = httpx.get(self._root("tx-log"), headers=headers)
        return req.text

    def tx_log_docs(self):
        headers = {"Accept": "application/json"}
        req = httpx.get(self._root("tx-log?with-ops?=true"), headers=headers)
        return req.text

    def submit_tx(self, txs) -> Any:
        res = self._client.post("/submit-tx", json={"tx-ops": txs})

        return res.json()

    def tx_committed(self, txid: int):
        headers = {"Accept": "application/json"}
        req = httpx.get(self._root(f"tx_commited?txId={txid}"), headers=headers)
        return req.text

    def latest_completed_tx(self):
        headers = {"Accept": "application/json"}
        req = httpx.get(self._root("latest-completed-tx"), headers=headers)
        return req.text

    def latest_submitted_tx(self):
        headers = {"Accept": "application/json"}
        req = httpx.get(self._root("latest-submitted-tx"), headers=headers)
        return req.text

    def active_queries(self):
        headers = {"Accept": "application/json"}
        req = httpx.get(self._root("active-queries"), headers=headers)
        return req.text

    def recent_queries(self):
        headers = {"Accept": "application/json"}
        req = httpx.get(self._root("recent-queries"), headers=headers)
        return req.text

    def slowest_queries(self):
        headers = {"Accept": "application/json"}
        req = httpx.get(self._root("recent-queries"), headers=headers)
        return req.text


def dispatch(xtdb, instruction):
    match instruction.pop(0):
        case "list-keys":
            return xtdb.query()
        case "list-values":
            return xtdb.query(
                "{:query {:find [(pull ?var [*])] :where [[?var :xt/id]]}}"
            )
        case "submit-tx":
            if instruction:
                return xtdb.submit_tx(instruction)
        case x:
            call = getattr(xtdb, x.replace("-", "_"))
            match call.__code__.co_argcount - 1:
                case 1:
                    return call(instruction[0])
                case 0:
                    return call()


KEYWORDS = set(
    [
        keyword.replace("_", "-")
        for keyword in dir(XTDBClient)
        if callable(getattr(XTDBClient, keyword)) and not keyword.startswith("_")
    ]
    + ["list-keys", "list-values"]
)

EPILOG = """
As instructions the following keywords with arguments are supported:
  status
  query [edn-query]
  list-keys
  list-values
  entity [xt/id]
  history [xt/id]
  entity-tx [xt/id]
  attribute-stats
  sync [timeout in ms]
  await-tx [transaction id]
  await-tx-time [time]
  tx-log
  tx-log-docs
  submit-tx [transaction list]
  tx-committed [transaction id]
  latest-completed-tx
  latest-submitted-tx
  active-queries
  recent-queries
  slowest-queries

If no keyword is given in the initial instruction either use
* a dash "-" to read stdin
* otherwise all instructions are treated as filenames

See https://v1-docs.xtdb.com/clients/http/ for more information.

OpenKAT https://openkat.nl/.
"""


def iparse(instructions):
    idxs = [idx for idx, key in enumerate(instructions) if key in KEYWORDS] + [
        len(instructions)
    ]
    return [
        instructions[i:j]
        for i, j in zip(idxs, idxs[1:] + idxs[:1])
        if instructions[i:j]
    ]


@click.group()
# @click.option("--debug/--no-debug", default=False)
@click.option("--timeout", default=5000, help="XTDB request timeout (in ms)")
@click.option(
    "--base-url", default="http://localhost:3000", help="XTDB server base url"
)
@click.argument("node", default="0", help="XTDB node")
@click.pass_context
def cli(ctx: click.Context, base_url: str, node: str, timeout: int):
    client = XTDBClient(base_url, node, timeout)

    ctx.ensure_object(dict)
    ctx.obj["client"] = client


@cli.command()
@click.argument(type=int)
@click.pass_context
def tx_committed(ctx: click.Context, txid: int) -> None:
    client = ctx.obj["client"]
    click.echo(client.tx_committed(txid))


# def main():
#     parser = argparse.ArgumentParser(
#         prog="xtdb-cli",
#         description="A command-line interface for xtdb multinode as used in OpenKAT",
#         epilog=EPILOG,
#         add_help=True,
#         allow_abbrev=True,
#         formatter_class=argparse.RawDescriptionHelpFormatter,
#     )
#     parser.add_argument(
#         "--port", help="xtdb server port (default 3000)", type=int, default=3000
#     )
#     parser.add_argument(
#         "--host",
#         help="xtdb server hostname (default localhost)",
#         type=str,
#         default="localhost",
#     )
#     parser.add_argument("--node", help="xtdb node (default 0)", type=str, default="0")
#     parser.add_argument("instructions", type=str, nargs="*")
#     args = parser.parse_args()
#     xtdb = XTDBClient(args.host, args.port, args.node)
#     if args.instructions:
#         if args.instructions[0] in KEYWORDS:
#             for instruction in iparse(args.instructions):
#                 result = dispatch(xtdb, instruction)
#                 if result:
#                     sys.stdout.write(f"{result}\n")
#         elif args.instructions[0] == "-":
#             for line in sys.stdin:
#                 if line.rstrip() == "exit" or line.rstrip() == "quit":
#                     break
#                 for instruction in iparse(line.rstrip().split(" ")):
#                     result = dispatch(xtdb, instruction)
#                     if result:
#                         sys.stdout.write(f"{result}\n")
#         else:
#             for fname in args.instructions:
#                 with Path(fname).open("r") as file:
#                     for line in file.readlines():
#                         if line.rstrip() == "exit" or line.rstrip() == "quit":
#                             break
#                         for instruction in iparse(line.rstrip().split(" ")):
#                             result = dispatch(xtdb, instruction)
#                             if result:
#                                 sys.stdout.write(f"{result}\n")


if __name__ == "__main__":
    cli()
