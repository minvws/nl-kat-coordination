import json
from os import getenv

SEARCHTARGET_DEFAULT = "ssdp:all"
TIMEOUT_DEFAULT = 10


def run_ssdp(search_targets: str, timeout: int) -> list[dict[str, str]]:
    from ssdpy import SSDPClient

    client = SSDPClient()
    return client.m_search(st=search_targets, mx=timeout)


def run(_) -> list[tuple[set, bytes | str]]:
    return [
        (
            set(),
            json.dumps(
                run_ssdp(
                    getenv("SEARCHTARGET", SEARCHTARGET_DEFAULT),
                    int(getenv("TIMEOUT", TIMEOUT_DEFAULT)),
                )
            ),
        )
    ]
