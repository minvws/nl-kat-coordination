#!/usr/bin/env python

import argparse
import datetime
import sys
from pathlib import Path

import httpx


class XTDB:
    def __init__(self, host: str, port: int, node: str):
        self.host = host
        self.port = port
        self.node = node

    def root(self, target: str = ""):
        return f"http://{self.host}:{self.port}/_xtdb/{self.node}/{target}"

    def status(self):
        headers = {"Accept": "application/json"}
        req = httpx.get(self.root("status"), headers=headers)
        return req.text

    def query(self, query: str = "{:query {:find [ ?var ] :where [[?var :xt/id ]]}}"):
        headers = {"Accept": "application/json", "Content-Type": "application/edn"}
        req = httpx.post(self.root("query"), headers=headers, data=query)
        return req.text

    def entity(self, key: str):
        headers = {"Accept": "application/json"}
        req = httpx.get(self.root(f"entity?eid={key}"), headers=headers)
        return req.text

    def history(self, key: str):
        headers = {"Accept": "application/json"}
        req = httpx.get(self.root(f"entity?eid={key}&history=true&sortOrder=asc"), headers=headers)
        return req.text

    def entity_tx(self, key: str):
        headers = {"Accept": "application/json"}
        req = httpx.get(self.root(f"entity-tx?eid={key}"), headers=headers)
        return req.text

    def attribute_stats(self):
        headers = {"Accept": "application/json"}
        req = httpx.get(self.root("attribute-stats"), headers=headers)
        return req.text

    def sync(self, timeout: int = 500):
        headers = {"Accept": "application/json"}
        req = httpx.get(self.root(f"sync?timeout={timeout}"), headers=headers)
        return req.text

    def await_tx(self, txid: int):
        headers = {"Accept": "application/json"}
        req = httpx.get(self.root(f"await-tx?txId={txid}"), headers=headers)
        return req.text

    def await_tx_time(self, tm: str = datetime.datetime.now().isoformat()):
        headers = {"Accept": "application/json"}
        req = httpx.get(self.root(f"await-tx-time?tx-time={tm}"), headers=headers)
        return req.text

    def tx_log(self):
        headers = {"Accept": "application/json"}
        req = httpx.get(self.root("tx-log"), headers=headers)
        return req.text

    def submit_tx(self, txs):
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        data = '{{"tx-ops": {}}}'.format(" ".join(txs))
        req = httpx.post(self.root("submit-tx"), headers=headers, data=data)
        return req.text

    def tx_committed(self, txid: int):
        headers = {"Accept": "application/json"}
        req = httpx.get(self.root(f"tx_commited?txId={txid}"), headers=headers)
        return req.text

    def latest_completed_tx(self):
        headers = {"Accept": "application/json"}
        req = httpx.get(self.root("latest-completed-tx"), headers=headers)
        return req.text

    def latest_submitted_tx(self):
        headers = {"Accept": "application/json"}
        req = httpx.get(self.root("latest-submitted-tx"), headers=headers)
        return req.text

    def active_queries(self):
        headers = {"Accept": "application/json"}
        req = httpx.get(self.root("active-queries"), headers=headers)
        return req.text

    def recent_queries(self):
        headers = {"Accept": "application/json"}
        req = httpx.get(self.root("recent-queries"), headers=headers)
        return req.text

    def slowest_queries(self):
        headers = {"Accept": "application/json"}
        req = httpx.get(self.root("recent-queries"), headers=headers)
        return req.text


def dispatch(xtdb, instruction):
    match instruction.pop(0):
        case "status":
            return xtdb.status()
        case "query":
            if instruction:
                return xtdb.query(instruction[0])
            else:
                return xtdb.query()
        case "list-keys":
            return xtdb.query()
        case "list-values":
            return xtdb.query("{:query {:find [(pull ?var [*])] :where [[?var :xt/id]]}}")
        case "entity":
            if instruction:
                return xtdb.entity(instruction[0])
        case "history":
            if instruction:
                return xtdb.entity(instruction[0])
        case "entity-tx":
            if instruction:
                return xtdb.entity(instruction[0])
        case "attribute-stats":
            return xtdb.attribute_stats()
        case "sync":
            if instruction:
                return xtdb.sync(instruction[0])
            else:
                return xtdb.sync()
        case "await-tx":
            if instruction:
                return xtdb.await_tx(instruction[0])
        case "await-tx-time":
            if instruction:
                return xtdb.await_tx_time(instruction[0])
        case "tx-log":
            return xtdb.tx_log()
        case "submit-tx":
            if instruction:
                return xtdb.submit_tx(instruction)
        case "tx-committed":
            if instruction:
                return xtdb.tx_committed(instruction.pop(0))
        case "latest-completed-tx":
            return xtdb.latest_completed_tx()
        case "latest-submitted-tx":
            return xtdb.latest_submitted_tx()
        case "active-queries":
            return xtdb.active_queries()
        case "recent-queries":
            return xtdb.recent_queries()
        case "slowest-queries":
            return xtdb.recent_queries()


KEYWORDS = [
    "status",
    "query",
    "list-keys",
    "list-values",
    "entity",
    "history",
    "entity-tx",
    "attribute-stats",
    "sync",
    "await-tx",
    "await-tx-time",
    "tx-log",
    "submit-tx",
    "tx-committed",
    "latest-completed-tx",
    "latest-submitted-tx",
    "active-queries",
    "recent-queries",
    "slowest-queries",
]

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
  submit-tx [transaction list]
  tx-committed [transaction id]
  latest-completed-tx
  latest-submitted-tx
  active-queries
  recent-queries
  slowest-queries
See https://v1-docs.xtdb.com/clients/http/ for more information.

OpenKAT https://openkat.nl/.
"""


def iparse(instructions):
    idxs = [idx for idx, key in enumerate(instructions) if key in KEYWORDS] + [len(instructions)]
    return [instructions[i:j] for i, j in zip(idxs, idxs[1:] + idxs[:1]) if instructions[i:j]]


def main():
    parser = argparse.ArgumentParser(
        prog="xtdb-cli",
        description="A command-line interface for xtdb multinode as used in OpenKAT",
        epilog=EPILOG,
        add_help=True,
        allow_abbrev=True,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--port", help="xtdb server port (default 3000)", type=int, default=3000)
    parser.add_argument("--host", help="xtdb server hostname (default localhost)", type=str, default="localhost")
    parser.add_argument("--node", help="xtdb node (default 0)", type=str, default="0")
    parser.add_argument("instructions", type=str, nargs="*")
    args = parser.parse_args()
    xtdb = XTDB(args.host, args.port, args.node)
    if args.instructions:
        if args.instructions[0] in KEYWORDS:
            for instruction in iparse(args.instructions):
                result = dispatch(xtdb, instruction)
                if result:
                    sys.stdout.write(f"{result}\n")
        elif args.instructions[0] == "-":
            for line in sys.stdin:
                if line.rstrip() == "exit" or line.rstrip() == "quit":
                    break
                for instruction in iparse(line.rstrip().split(" ")):
                    result = dispatch(xtdb, instruction)
                    if result:
                        sys.stdout.write(f"{result}\n")
        else:
            for fname in args.instructions:
                with Path(fname).open("r") as file:
                    for line in file.readlines():
                        if line.rstrip() == "exit" or line.rstrip() == "quit":
                            break
                        for instruction in iparse(line.rstrip().split(" ")):
                            result = dispatch(xtdb, instruction)
                            if result:
                                sys.stdout.write(f"{result}\n")


if __name__ == "__main__":
    main()
