import json
import re
from typing import Tuple, Union
from urllib.parse import quote_plus

import requests

from config import settings
from job import BoefjeMeta


def run(boefje_meta: BoefjeMeta) -> Tuple[BoefjeMeta, Union[bytes, str]]:
    pk = boefje_meta.input_ooi
    results = []
    if re.match(pk, "IPAddressV4|.*") or re.match(pk, "IPAddressV6|.*"):
        ip = pk.split("|")[-1]
        dork = quote_plus(f"+ip:{ip}")
    elif re.match(pk, "Hostname|.*"):
        hostname = pk.split("|")[-1]
        dork = quote_plus(f'+host:"{hostname}"')
    else:
        raise NameError(f'Expected an IPAddress of Hostname, but got pk "{pk}"')

    for type in ("leak", "service"):
        page_counter = 0
        want_next_result = True
        while want_next_result:
            want_next_result = False
            response = requests.get(
                f"https://leakix.net/search?scope={type}&q={dork}&page={page_counter}",
                headers={"Accept": "application/json", "api-key": settings.leakix_api},
            )
            page_counter += 1
            if not response:
                break
            response_json = response.json()
            if not response_json:
                break

            for event in response_json:
                if not event["event_fingerprint"]:
                    continue
                want_next_result = True
                results.append(event)

    return boefje_meta, json.dumps(results)
