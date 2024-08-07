from ipaddress import ip_address

import requests

from boefjes.job_models import BoefjeMeta

REQUEST_TIMEOUT = 60


def run(boefje_meta: BoefjeMeta) -> list[tuple[set, bytes | str]]:
    """Make request to InternetDB."""
    ip = boefje_meta.arguments["input"]["address"]
    if ip_address(ip).is_private:
        return [({"info/boefje"}, "Skipping private IP address")]
    response = requests.get(f"https://internetdb.shodan.io/{ip}", timeout=REQUEST_TIMEOUT)
    response.raise_for_status()

    return [(set(), response.content)]
