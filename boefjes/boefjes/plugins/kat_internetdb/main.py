import json
import logging
from ipaddress import ip_address

import requests

from boefjes.job_models import BoefjeMeta

REQUEST_TIMEOUT = 60


def run(boefje_meta: BoefjeMeta) -> list[tuple[set, bytes | str]]:
    """Make request to InternetDB."""
    ip = boefje_meta.arguments["input"]["address"]
    results = {}
    if ip_address(ip).is_private:
        logging.info("Private IP requested, I will not forward this to Shodan InternetDB.")
    else:
        try:
            results = requests.get(f"https://internetdb.shodan.io/{ip}", timeout=REQUEST_TIMEOUT).json()
        except requests.exceptions.RequestException as exc:
            logging.warning(exc)

    return [(set(), json.dumps(results))]
