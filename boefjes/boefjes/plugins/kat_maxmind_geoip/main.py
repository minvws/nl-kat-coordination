import hashlib
import io
import json
import os
import tarfile
import tempfile
from datetime import datetime
from os import getenv
from pathlib import Path

import requests
from netaddr import IPAddress, IPNetwork

from boefjes.job_models import BoefjeMeta

BASE_PATH = Path(getenv("OPENKAT_CACHE_PATH", Path(__file__).parent))
GEOIP_PATH = BASE_PATH / "geoip.json"
GEOIP_META_PATH = BASE_PATH / "geoip-meta.json"
GEOIP_SOURCE_URL = "https://download.maxmind.com/geoip/databases/GeoLite2-City/download?suffix=tar.gz"
GEOIP_CACHE_TIMEOUT = 7200  # in seconds
HASHFUNC = "sha256"


def run(boefje_meta: BoefjeMeta) -> list[tuple[set, bytes | str]]:
    input_ = boefje_meta.arguments["input"]
    ip = input_["address"]
    now = datetime.utcnow()
    hash_algorithm = getenv("HASHFUNC", HASHFUNC)

    if not GEOIP_PATH.exists() or cache_out_of_date():
        geoip_json, geoip_meta = refresh_geoip(hash_algorithm)
    else:
        with GEOIP_PATH.open() as json_file:
            geoip_json = json.load(json_file)
        with GEOIP_META_PATH.open() as json_meta_file:
            geoip_meta = json.load(json_meta_file)
    exists = False
    notexpired = False
    roas = []
    for roa in geoip_json["roas"]:
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
            {"geoip/cache-meta"},
            json.dumps(geoip_meta),
        ),
    ]


def create_hash(data: bytes, algo: str) -> str:
    hashfunc = getattr(hashlib, algo)
    return hashfunc(data).hexdigest()


def cache_out_of_date() -> bool:
    """Returns True if the file is older than the allowed cache_timout"""
    now = datetime.utcnow()
    maxage = int(getenv("GEOIP_CACHE_TIMEOUT", GEOIP_CACHE_TIMEOUT))
    with GEOIP_META_PATH.open() as meta_file:
        meta = json.load(meta_file)
    cached_file_timestamp = datetime.strptime(meta["timestamp"], "%Y-%m-%dT%H:%M:%SZ")
    return (now - cached_file_timestamp).total_seconds() > maxage


def refresh_geoip(algo: str) -> tuple[dict, dict]:
    source_url = getenv("GEOIP_SOURCE_URL", GEOIP_SOURCE_URL)
    response = requests.get(source_url, allow_redirects=True, timeout=30)
    response.raise_for_status()

    file_like_object = io.BytesIO(response.content)

    with tarfile.open("r:gz", fileobj=file_like_object) as tf:
        tf.extract("GeoLite2-City_20240712/GeoLite2-City.mmdb", BASE_PATH)

    with tempfile.NamedTemporaryFile(mode="wb", dir=GEOIP_PATH.parent, delete=False) as temp_geoip_file:
        temp_geoip_file.write(response.content)
        # atomic operation
        os.rename(temp_geoip_file.name, GEOIP_PATH)
    metadata = {
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": source_url,
        "hash": create_hash(response.content, algo),
        "hash_algorithm": algo,
    }
    with open(GEOIP_META_PATH, "w") as meta_file:
        json.dump(metadata, meta_file)
    return (json.loads(response.content), metadata)
