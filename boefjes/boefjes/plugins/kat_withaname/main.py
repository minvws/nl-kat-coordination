from ipaddress import ip_address
from os import getenv

import httpx

REQUEST_TIMEOUT = 60


def run(boefje_meta: dict) -> list[tuple[set, bytes | str]]:
    """Make request to witha.name."""
    ip = ip_address(boefje_meta["arguments"]["input"]["address"])
    if ip.is_private or ip.is_multicast or ip.is_reserved:
        return [({"info/boefje"}, "Skipping private/multicast/reserved IP address")]

    response = httpx.get("https://witha.name/data/last.json", timeout=int(getenv("REQUEST_TIMEOUT", REQUEST_TIMEOUT)))

    response.raise_for_status()

    return [(set(), response.content)]
