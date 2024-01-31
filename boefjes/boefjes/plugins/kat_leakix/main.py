import json
import re
from os import getenv
from typing import List, Tuple, Union
from urllib.parse import quote_plus

import requests

from boefjes.job_models import BoefjeMeta


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    pk = boefje_meta.input_ooi
    results = []
    if re.match(pk, "IPAddressV4|.*") or re.match(pk, "IPAddressV6|.*"):
        ip = pk.split("|")[-1]
        query = quote_plus(f"+ip:{ip}")
    elif re.match(pk, "Hostname|.*"):
        hostname = pk.split("|")[-1]
        query = quote_plus(f'+host:"{hostname}"')
    else:
        raise NameError(f'Expected an IPAddress or Hostname, but got pk "{pk}"')

    for scope in ("leak", "service"):
        page_counter = 0
        want_next_result = True
        while want_next_result:
            want_next_result = False
            response = requests.get(
                f"https://leakix.net/search?scope={scope}&q={query}&page={page_counter}",
                headers={"Accept": "application/json", "api-key": getenv("LEAKIX_API")},
            )
            page_counter += 1
            if not response or not response.content:
                break
            response_json = response.json()
            if not response_json:
                break

            for event in response_json:
                if not event["event_fingerprint"]:
                    continue
                want_next_result = True
                results.append(event)

    return [(set(), json.dumps(results))]
