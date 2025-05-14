from ipaddress import ip_address
from os import getenv

import httpx

REQUEST_TIMEOUT = 60


def run(boefje_meta: dict) -> list[tuple[set, bytes | str]]:
    """Make request to AbuseIPDB."""

    if boefje_meta["arguments"]["input"]["network"]["name"] != "internet":
        return [({"info/boefje"}, "Skipping non-internet network")]

    ip_raw = str(boefje_meta["arguments"]["input"]["address"])
    ip = ip_address(ip_raw)

    # Skip private, multicast, or reserved IP addresses
    if ip.is_private or ip.is_multicast or ip.is_reserved:
        return [({"info/boefje"}, "Skipping private, multicast, or reserved IP address")]

    api_key = getenv("ABUSEIPDB_API", "")
    if api_key == "":
        return [({"error/boefje"}, "No AbuseIPDB API key provided")]

    response = httpx.get(
        "https://api.abuseipdb.com/api/v2/check",
        params={"ipAddress": ip_raw, "verbose": "true", "maxAgeInDays": getenv("MAX_AGE_DAYS", "30")},
        headers={"Key": api_key, "Accept": "application/json"},
        timeout=int(getenv("REQUEST_TIMEOUT", REQUEST_TIMEOUT)),
    )
    response.raise_for_status()

    return [(set(), response.content)]
