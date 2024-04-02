"""Boefje script for validating vrps records based on code from @trideeindhoven"""

import hashlib
import json
import os
import tempfile
from datetime import datetime
from os import getenv
from pathlib import Path

import requests
from netaddr import IPAddress, IPNetwork

from boefjes.job_models import BoefjeMeta

# Paths and URLs for RPKI
BASE_PATH = Path(getenv("OPENKAT_CACHE_PATH", Path(__file__).parent))
RPKI_PATH = BASE_PATH / "rpki.json"
RPKI_META_PATH = BASE_PATH / "rpki-meta.json"
RPKI_SOURCE_URL = "https://console.rpki-client.org/vrps.json"

# Paths and URLs for BGP
BGP_PATH = BASE_PATH / "bgp.jsonl"
BGP_META_PATH = BASE_PATH / "bgp-meta.json"
BGP_SOURCE_URL = "https://bgp.tools/table.jsonl"

# Cache timeout and default hash function
RPKI_CACHE_TIMEOUT = 1800  # in seconds
HASHFUNC = "sha256"


def run(boefje_meta: BoefjeMeta) -> list[tuple[set, bytes | str]]:
    input_ = boefje_meta.arguments["input"]
    ip = input_["address"]
    hash_algorithm = getenv("HASHFUNC", HASHFUNC)

    # RPKI cache check and refresh
    if not RPKI_PATH.exists() or cache_out_of_date(RPKI_META_PATH):
        rpki_json, rpki_meta = refresh_cache(RPKI_SOURCE_URL, RPKI_PATH, RPKI_META_PATH, hash_algorithm)
    else:
        rpki_json = load_json(RPKI_PATH)
        rpki_meta = load_json(RPKI_META_PATH)

    if not BGP_PATH.exists() or cache_out_of_date(BGP_META_PATH):
        bgp_data, bgp_meta = refresh_cache(
            BGP_SOURCE_URL, BGP_PATH, BGP_META_PATH, hash_algorithm, file_extension="jsonl"
        )
    else:
        bgp_data = load_jsonl(BGP_PATH)

    exists = False
    valid = False
    roas = []
    bgp_entries = []
    for roa in rpki_json["roas"]:
        if IPAddress(ip) in IPNetwork(roa["prefix"]):
            expires = datetime.fromtimestamp(roa["expires"])
            asn = roa["asn"]
            roas.append(
                {"prefix": roa["prefix"], "expires": expires.strftime("%Y-%m-%dT%H:%M"), "ta": roa["ta"], "asn": asn}
            )
            exists = True

            # check validity through bgp json
            for entry in bgp_data:
                if IPAddress(ip) in IPNetwork(entry["CIDR"]):
                    bgp_entries.append(entry)
                    if entry["ASN"] == asn:
                        valid = True

    results = {"vrps_records": roas, "exists": exists, "bgp_entries": bgp_entries, "valid": valid}

    return [
        (set(), json.dumps(results)),
        (
            {"rpki/cache-meta"},
            json.dumps(rpki_meta),
        ),
    ]


def cache_out_of_date(meta_path: Path) -> bool:
    """Returns True if the cache file is older than the allowed cache_timeout"""
    now = datetime.utcnow()
    maxage = getenv("RPKI_CACHE_TIMEOUT", RPKI_CACHE_TIMEOUT)
    meta = load_json(meta_path)
    cached_file_timestamp = datetime.strptime(meta["timestamp"], "%Y-%m-%dT%H:%M:%SZ")
    return (now - cached_file_timestamp).total_seconds() > maxage


def refresh_cache(
    source_url: str, data_path: Path, meta_path: Path, algo: str, file_extension: str = "json"
) -> tuple[dict | list, dict]:
    """Refreshes the cache for either RPKI or BGP data. Handles both JSON and JSON Lines formats."""
    headers = {"User-Agent": getenv("USERAGENT", default="OpenKAT")}
    response = requests.get(source_url, headers=headers, allow_redirects=True, timeout=30)
    response.raise_for_status()

    with tempfile.NamedTemporaryFile(mode="wb", dir=data_path.parent, delete=False) as temp_file:
        temp_file.write(response.content)
        # Atomic operation to move temp file to permanent location
        os.rename(temp_file.name, data_path)

    # Processing the response content based on format
    if file_extension == "json":
        data = json.loads(response.content)
    elif file_extension == "jsonl":
        # For JSON Lines, parse each line separately
        data = [json.loads(line) for line in response.content.decode().splitlines()]
    else:
        raise ValueError(f"Unsupported format: {file_extension}")

    # Creating metadata
    metadata = {
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": source_url,
        "hash": create_hash(response.content, algo),
        "hash_algorithm": algo,
    }
    with open(meta_path, "w") as meta_file:
        json.dump(metadata, meta_file)

    return data, metadata


def create_hash(data: bytes, algo: str) -> str:
    hashfunc = getattr(hashlib, algo)
    return hashfunc(data).hexdigest()


def load_json(path: Path) -> dict:
    """Utility function to load a JSON file"""
    with path.open() as json_file:
        return json.load(json_file)


def load_jsonl(path: Path) -> list:
    """Utility function to load a JSON Lines file"""
    with path.open("r") as file:
        return [json.loads(line) for line in file]
