"""Boefje script for exporting OOI's to an external http api"""

import json
from contextlib import suppress
from os import getenv

import requests


def run(boefje_meta: dict) -> list[tuple[set, bytes | str]]:
    input_ooi = boefje_meta["arguments"]["input"]

    timeout = getenv("TIMEOUT", default=15)
    endpoint_uri = getenv("EXPORT_HTTP_ENDPOINT", "")
    request_headers = getenv("EXPORT_REQUEST_HEADERS", "")
    request_parameter = getenv("EXPORT_REQUEST_PARAMETER", "")
    request_verb = getenv("EXPORT_HTTP_VERB", default="POST").lower()
    useragent = getenv("USERAGENT", default="OpenKAT")
    organization = getenv("", boefje_meta["organization"])

    headers = {"User-Agent": useragent}
    if request_headers:
        request_header_list = request_headers.split("\n")
        for request_header in request_header_list:
            request_header_tuple = request_header.split(":")
            with suppress(IndexError):
                headers[request_header_tuple[0]] = request_header_tuple[1]

    session = requests.Session()
    if request_verb == "get":
        response = session.get(
            endpoint_uri,
            params={request_parameter: json.dumps(input_ooi), "organization": organization},
            headers=headers,
            timeout=float(timeout),
        )
    else:
        data = None
        jsondata = None
        if request_parameter:
            data = {request_parameter: json.dumps(input_ooi), "organization": organization}
        else:
            jsondata = input_ooi

        response = session.request(
            request_verb, endpoint_uri, data=data, json=jsondata, headers=headers, timeout=float(timeout)
        )
    if not response.ok:
        raise ValueError(response.content)

    return [(set(), response.content)]
