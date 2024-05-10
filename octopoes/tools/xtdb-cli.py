#!/usr/bin/env python

import datetime
from typing import Any

import click
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

    def sync(self, timeout: int = 500) -> Any:
        res = self._client.get("/sync", params={"timeout": timeout})

        return res.json()

    def await_tx(self, transaction_id: int) -> Any:
        res = self._client.get(f"/await-tx", params={"txId": transaction_id})

        return res.json()

    def await_tx_time(self, transaction_time: str | None = None) -> Any:
        if transaction_time is None:
            transaction_time = datetime.datetime.now().isoformat()

        res = self._client.get(f"/await-tx-time", params={"tx-time": transaction_time})

        return res.json()

    def tx_log(self) -> Any:
        res = self._client.get("/tx-log")

        return res.json()

    def tx_log_docs(self) -> Any:
        res = self._client.get("/tx-log", params={"with-ops": "true"})

        return res.json()

    def submit_tx(self, transactions: list[str]) -> Any:
        res = self._client.post("/submit-tx", json={"tx-ops": transactions})

        return res.json()

    def tx_committed(self, txid: int) -> Any:
        res = self._client.get(f"/tx-committed", params={"txId": txid})

        return res.json()

    def latest_completed_tx(self) -> Any:
        res = self._client.get("/latest-completed-tx")

        return res.json()

    def latest_submitted_tx(self) -> Any:
        res = self._client.get("/latest-submitted-tx")

        return res.json()

    def active_queries(self) -> Any:
        res = self._client.get("/active-queries")

        return res.json()

    def recent_queries(self) -> Any:
        res = self._client.get("/recent-queries")
        return res.json()

    def slowest_queries(self) -> Any:
        res = self._client.get("/recent-queries")
        return res.json()


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


@click.group
@click.option("--debug/--no-debug", default=False, help="Verbose output")
@click.option("--timeout", type=int, default=5000, help="XTDB request timeout (in ms)")
@click.option(
    "--base-url", default="http://localhost:3000", help="XTDB server base url"
)
@click.option("node", default="0", help="XTDB node")
@click.pass_context
def cli(ctx: click.Context, base_url: str, node: str, timeout: int, debug: bool):
    client = XTDBClient(base_url, node, timeout)

    ctx.ensure_object(dict)
    ctx.obj["client"] = client


@cli.command
@click.pass_context
def status(ctx: click.Context):
    client: XTDBClient = ctx.obj["client"]

    click.echo(client.status())


@cli.command
@click.argument
@click.pass_context
def query(ctx: click.Context, query: str):
    client: XTDBClient = ctx.obj["client"]

    click.echo(client.query(query))


@cli.command
@click.argument
@click.pass_context
def entity(ctx: click.Context, key: str):
    client: XTDBClient = ctx.obj["client"]

    click.echo(client.entity(key))


@cli.command
@click.argument
@click.pass_context
def history(ctx: click.Context, key: str):
    client: XTDBClient = ctx.obj["client"]

    click.echo(client.history(key))


@cli.command
@click.argument
@click.pass_context
def entity_tx(ctx: click.Context, key: str):
    client: XTDBClient = ctx.obj["client"]

    click.echo(client.entity_tx(key))


@cli.command
@click.pass_context
def attribute_stats(ctx: click.Context):
    client: XTDBClient = ctx.obj["client"]

    click.echo(client.attribute_stats())


@cli.command
@click.argument("timeout", type=int)
@click.pass_context
def sync(ctx: click.Context, timeout: int):
    client: XTDBClient = ctx.obj["client"]

    click.echo(client.sync(timeout))


@cli.command
@click.argument("tx-id", type=int)
@click.pass_context
def await_tx(ctx: click.Context, transaction_id: int):
    client: XTDBClient = ctx.obj["client"]


@cli.command
@click.option("tx-time", type=click.DateTime())  # todo: find out how this exactly works
@click.pass_context
def await_tx_time(
    ctx: click.Context, transaction_time: datetime.datetime | None = None
):
    client: XTDBClient = ctx.obj["client"]

    click.echo(client.await_tx_time(transaction_time))


@cli.command
@click.pass_context
def tx_log(ctx: click.Context):
    client: XTDBClient = ctx.obj["client"]

    click.echo(client.tx_log())


@cli.command
@click.pass_context
def tx_log_docs(ctx: click.Context):
    client: XTDBClient = ctx.obj["client"]

    click.echo(client.tx_log_docs())


@cli.command
@click.argument("txs", nargs=-1)
@click.pass_context
def submit_tx(ctx: click.Context, transactions):
    client: XTDBClient = ctx.obj["client"]

    click.echo(client.submit_tx(transactions))


@cli.command
@click.argument("tx-id", type=int)
@click.pass_context
def tx_committed(ctx: click.Context, transaction_id: int) -> None:
    client: XTDBClient = ctx.obj["client"]

    click.echo(client.tx_committed(transaction_id))


@cli.command
@click.pass_context
def latest_completed_tx(ctx: click.Context):
    client: XTDBClient = ctx.obj["client"]

    click.echo(client.latest_completed_tx())


@cli.command
@click.pass_context
def latest_submitted_tx(ctx: click.Context):
    client: XTDBClient = ctx.obj["client"]

    click.echo(client.latest_submitted_tx())


@cli.command
@click.pass_context
def active_queries(ctx: click.Context):
    client: XTDBClient = ctx.obj["client"]

    click.echo(client.active_queries())


@cli.command
@click.pass_context
def recent_queries(ctx: click.Context):
    client: XTDBClient = ctx.obj["client"]

    click.echo(client.recent_queries())


@cli.command
@click.pass_context
def slowest_queries(ctx: click.Context):
    client: XTDBClient = ctx.obj["client"]

    click.echo(client.slowest_queries())


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
