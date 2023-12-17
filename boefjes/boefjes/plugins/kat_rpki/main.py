"""Boefje script for validating vrps records based on code from @trideeindhoven"""
import json
import os
from datetime import datetime
from os import getenv
from typing import Bool, Dict, List, Tuple, Union

import requests
from netaddr import IPAddress, IPNetwork

from boefjes.job_models import BoefjeMeta

RPKI_PATH = "boefjes/plugins/kat_rpki/rpki.json"
RPKI_META_PATH = "boefjes/plugins/kat_rpki/rpki-meta.json"
RPKI_SOURCE_URL = "https://console.rpki-client.org/vrps.json"
RPKI_CACHE_TIMEOUT = 1800  # in seconds


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    input_ = boefje_meta.arguments["input"]
    ip = input_["address"]
    now = datetime.utcnow()

    if not os.path.exists(RPKI_PATH) or not validate_age():
        rpki_json = refresh_rpki()
    else:
        with open(RPKI_PATH) as json_file:
            rpki_json = json.load(json_file)

    exists = False
    valid = False
    roas = []
    for roa in rpki_json["roas"]:
        if IPAddress(ip) in IPNetwork(roa["prefix"]):
            exists = True
            expires = datetime.fromtimestamp(roa["expires"])
            roas.append({"prefix": roa["prefix"], "expires": expires.strftime("%Y-%m-%dT%H:%M"), "ta": roa["ta"]})
            if expires > now:
                valid = True

    results = {"vrps_records": roas, "valid": valid, "exists": exists}

    return [(set(), json.dumps(results))]


def validate_age() -> Bool:
    now = datetime.utcnow()
    maxage = getenv("RPKI_CACHE_TIMEOUT") or RPKI_CACHE_TIMEOUT
    with open(RPKI_META_PATH) as meta_file:
        meta = json.load(meta_file)
    cached_file_timestamp = datetime.strptime(meta["timestamp"], "%Y-%m-%dT%H:%M:%SZ")
    return (now - cached_file_timestamp.total_seconds()) > maxage


def refresh_rpki() -> Dict:
    source_url = getenv("RPKI_SOURCE_URL") or RPKI_SOURCE_URL
    response = requests.get(source_url, allow_redirects=True)
    response.raise_for_status()
    with open(RPKI_PATH, "w") as prki_file:
        prki_file.write(response.content)
    metadata = {"timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), "source": source_url}
    with open(RPKI_META_PATH, "w") as meta_file:
        meta_file.write(json.dump(metadata))
    return json.loads(response.content)
