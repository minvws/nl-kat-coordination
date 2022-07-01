import json
from typing import Tuple, Union

import requests

from job import BoefjeMeta

CRT_SH_API = "https://crt.sh/"
MATCHES = ("=", "ILIKE", "LIKE", "single", "any", "FTS")
SEARCH_TYPES = (
    "c",
    "id",
    "ctid",
    "serial",
    "ski",
    "spkisha1",
    "spkisha256",
    "subjectsha1",
    "sha1",
    "sha256",
    "ca",
    "CAID",
    "CAName",
    "Identity",
    "CN",
    "E",
    "OU",
    "O",
    "dNSName",
    "rfc822Name",
    "iPAddress",
)


def request_certs(
    search_string, search_type="Identity", match="=", deduplicate=True, json_output=True
) -> str:
    """Queries the public service CRT.sh for certificate information
    the searchtype can be specified and defaults to Identity.
    the type of sql matching can be specified and defaults to "="
    Deduplication is on by default and the output is returned as a json string or html.
    """
    if match not in MATCHES:
        match = MATCHES[0]
    if search_type not in SEARCH_TYPES:
        search_type = "Identity"
    query = {search_type: search_string, "match": match}
    if json_output:
        query["output"] = "json"
    if deduplicate:
        query["deduplicate"] = "Y"

    response = requests.get(CRT_SH_API, query)
    if response.status_code != 200:
        response.raise_for_status()
    if json_output:
        return json.dumps(response.json())
    return response.text


def run(boefje_meta: BoefjeMeta) -> Tuple[BoefjeMeta, Union[bytes, str]]:
    input_ = boefje_meta.arguments["input"]
    fqdn = input_["hostname"]["name"]
    domain = fqdn if not fqdn.endswith(".") else fqdn[:-1]
    results = request_certs(domain)

    return boefje_meta, results
