import hashlib
import io
import json
import tarfile
from datetime import datetime
from os import getenv
from pathlib import Path

import maxminddb
import requests

from boefjes.job_models import BoefjeMeta

BASE_PATH = Path(getenv("OPENKAT_CACHE_PATH", Path(__file__).parent))
GEOIP_PATH = BASE_PATH / "geoip.json"
GEOIP_META_PATH = BASE_PATH / "geoip-meta.json"
GEOIP_SOURCE_URL = "https://download.maxmind.com/geoip/databases/GeoLite2-City/download?suffix=tar.gz"
GEOIP_CACHE_TIMEOUT = 7200  # in seconds
HASHFUNC = "sha256"


def run(boefje_meta: BoefjeMeta) -> list[tuple[set, bytes | str]]:
    input_ = boefje_meta.arguments["input"]
    hash_algorithm = getenv("HASHFUNC", HASHFUNC)

    if not GEOIP_PATH.exists() or cache_out_of_date():
        geoip_meta = refresh_geoip(hash_algorithm)
    else:
        with GEOIP_META_PATH.open() as json_meta_file:
            geoip_meta = json.load(json_meta_file)

    with maxminddb.open_database(
        "boefjes/plugins/kat_maxmind_geoip/GeoLite2-City_20240712/GeoLite2-City.mmdb"
    ) as reader:
        results = reader.get(input_["address"])

    return [
        ({"geoip/geo_data"}, json.dumps(results)),
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


def refresh_geoip(algo: str) -> dict:
    maxmind_username = getenv("MAXMIND_USERNAME", "")
    maxmind_password = getenv("MAXMIND_PASSWORD", "")
    source_url = getenv("GEOIP_SOURCE_URL", GEOIP_SOURCE_URL)
    response = requests.get(source_url, allow_redirects=True, timeout=30, auth=(maxmind_username, maxmind_password))
    response.raise_for_status()

    file_like_object = io.BytesIO(response.content)

    with tarfile.open("r:gz", fileobj=file_like_object) as tf:
        tf.extract("GeoLite2-City_20240712/GeoLite2-City.mmdb", BASE_PATH)

    metadata = {
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": source_url,
        "hash": create_hash(response.content, algo),
        "hash_algorithm": algo,
    }
    return metadata
