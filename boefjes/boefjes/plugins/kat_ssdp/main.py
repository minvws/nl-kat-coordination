import json
from os import getenv

from ssdpy import SSDPClient

SEARCHTARGET_DEFAULT = "ssdp:all"
TIMEOUT_DEFAULT = 10


def run_ssdp(search_targets: str, timeout: int) -> list[dict[str, str]]:
    client = SSDPClient()
    return client.m_search(st=search_targets, mx=timeout)


def run(_) -> list[tuple[set, bytes | str]]:
    return [
        (
            set(),
            json.dumps(run_ssdp(getenv("SEARCHTARGET", SEARCHTARGET_DEFAULT), int(getenv("TIMEOUT", TIMEOUT_DEFAULT)))),
        )
    ]
