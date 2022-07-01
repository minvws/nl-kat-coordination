import json
from typing import Tuple, Union
from job import BoefjeMeta

import requests
from urllib.parse import urlparse, urlunsplit
from forcediphttpsadapter.adapters import ForcedIPHTTPSAdapter


def run(boefje_meta: BoefjeMeta) -> Tuple[BoefjeMeta, Union[bytes, str]]:
    input_ = boefje_meta.arguments["input"]

    port = f":{input_['web_url']['port']}"
    netloc = (
        input_["web_url"]["netloc"]["address"]
        if "address" in input_["web_url"]["netloc"]
        else input_["web_url"]["netloc"]["name"]
    )

    url = f"{input_['web_url']['scheme']}://{netloc}{port}{input_['web_url']['path']}"
    ip = input_["website"]["ip_service"]["ip_port"]["address"]["address"]

    # Code from https://github.com/Roadmaster/forcediphttpsadapter/blob/master/example.py
    uri = url
    url_parts = urlparse(uri)
    hostname = url_parts.netloc
    session = requests.Session()

    if url_parts.scheme == "https":
        # Adapter is available, use it regardless of Python version
        base_url = urlunsplit((url_parts.scheme, url_parts.netloc, "", "", ""))
        session.mount(base_url, ForcedIPHTTPSAdapter(dest_ip=ip))
    else:
        # Fall back to old hack-ip-into-url behavior, for either
        # https with no adapter, or http.
        if ip:
            url_parts = url_parts._replace(netloc=ip)
            uri = urlunsplit(
                [
                    url_parts.scheme,
                    url_parts.netloc,
                    url_parts.path,
                    url_parts.query,
                    url_parts.fragment,
                ]
            )

    try:
        response = session.get(
            uri,
            headers={"Host": hostname, "Accept": "application/json"},
            verify=False,
            allow_redirects=False,
        )
        result = {
            # "content": response.content,
            "cookies": response.cookies.get_dict(),
            "headers": dict(response.headers),
            "code": response.status_code,
            "text": response.text,
        }
    except requests.exceptions.ConnectionError:
        result = {}

    return boefje_meta, json.dumps(result)
