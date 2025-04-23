from ipaddress import ip_address
from os import getenv

import httpx

from boefjes.job_models import BoefjeMeta

REQUEST_TIMEOUT = 60


def run(boefje_meta: BoefjeMeta) -> list[tuple[set, bytes | str]]:
    """Make request to InternetDB."""
    ip = boefje_meta.arguments["input"]["address"]
    ipinfo = ip_address(ip)
    if ipinfo.is_private or ipinfo.is_multicast or ipinfo.is_reserved:
        return [({"info/boefje"}, "Skipping private/multicast/reserved IP address")]

    url = f"https://api.abuseipdb.com/api/v2/check?ipAddress={ip_address}"
    headers = {"Key": getenv("ABUSEIPDB_API", ""), "Accept": "application/json"}

    response = httpx.get(url, headers=headers, timeout=int(getenv("REQUEST_TIMEOUT", REQUEST_TIMEOUT)))
    if response.status_code != httpx.codes.NOT_FOUND:
        response.raise_for_status()

    return [(set(), response.content)]
