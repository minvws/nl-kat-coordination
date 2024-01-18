"""Boefje script for validating vrps records based on code from @trideeindhoven"""
import hashlib
import json
import os
import tempfile
from datetime import datetime
from os import getenv
from pathlib import Path
from typing import Dict, List, Tuple, Union

import requests
from netaddr import IPAddress, IPNetwork

from boefjes.job_models import BoefjeMeta

BASE_PATH = Path(getenv("OPENKAT_CACHE_PATH", Path(__file__).parent))
RPKI_PATH = BASE_PATH / "rpki.json"
RPKI_META_PATH = BASE_PATH / "rpki-meta.json"
RPKI_SOURCE_URL = "https://console.rpki-client.org/vrps.json"
RPKI_CACHE_TIMEOUT = 1800  # in seconds
HASHFUNC = "sha256"


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    input_ = boefje_meta.arguments["input"]
    ip = input_["address"]
    now = datetime.utcnow()
    hash_algorithm = getenv("HASHFUNC", HASHFUNC)

    if not RPKI_PATH.exists() or cache_out_of_date():
        rpki_json, rpki_meta = refresh_rpki(hash_algorithm)
    else:
        with RPKI_PATH.open() as json_file:
            rpki_json = json.load(json_file)
        with RPKI_META_PATH.open() as json_meta_file:
            rpki_meta = json.load(json_meta_file)
    exists = False
    notexpired = False
    roas = []
    for roa in rpki_json["roas"]:
        if IPAddress(ip) in IPNetwork(roa["prefix"]):
            exists = True
            expires = datetime.fromtimestamp(roa["expires"])
            roas.append({"prefix": roa["prefix"], "expires": expires.strftime("%Y-%m-%dT%H:%M"), "ta": roa["ta"]})
            if expires > now:
                notexpired = True

    results = {"vrps_records": roas, "notexpired": notexpired, "exists": exists}

    return [
        (set(), json.dumps(results)),
        (
            set(
                "rpki/cache-meta",
            ),
            json.dumps(rpki_meta),
        ),
    ]


def create_hash(data: bytes, algo: str) -> str:
    hashfunc = getattr(hashlib, algo)
    return hashfunc(data).hexdigest()


def cache_out_of_date() -> bool:
    """Returns True if the file is older than the allowed cache_timout"""
    now = datetime.utcnow()
    maxage = getenv("RPKI_CACHE_TIMEOUT", RPKI_CACHE_TIMEOUT)
    with RPKI_META_PATH.open() as meta_file:
        meta = json.load(meta_file)
    cached_file_timestamp = datetime.strptime(meta["timestamp"], "%Y-%m-%dT%H:%M:%SZ")
    return (now - cached_file_timestamp).total_seconds() > maxage


def refresh_rpki(algo: str) -> Tuple[Dict, Dict]:
    source_url = getenv("RPKI_SOURCE_URL", RPKI_SOURCE_URL)
    response = requests.get(source_url, allow_redirects=True)
    response.raise_for_status()
    with tempfile.NamedTemporaryFile(mode="wb", dir=RPKI_PATH.parent, delete=False) as temp_rpki_file:
        temp_rpki_file.write(response.content)
        # atomic operation
        os.rename(temp_rpki_file.name, RPKI_PATH)
    metadata = {
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": source_url,
        "hash": create_hash(response.content, algo),
        "hash_algorithm": algo,
    }
    with open(RPKI_META_PATH, "w") as meta_file:
        json.dump(metadata, meta_file)
    return (json.loads(response.content), metadata)
