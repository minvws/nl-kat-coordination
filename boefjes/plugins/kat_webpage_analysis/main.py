import json
from typing import Tuple, Union, List
from boefjes.job_models import BoefjeMeta

from os import getenv
import requests
from urllib.parse import urlparse, urlunsplit
from forcediphttpsadapter.adapters import ForcedIPHTTPSAdapter


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    input_ = boefje_meta.arguments["input"]

    port = f":{input_['web_url']['port']}"
    netloc = (
        input_["web_url"]["netloc"]["address"]
        if "address" in input_["web_url"]["netloc"]
        else input_["web_url"]["netloc"]["name"]
    )

    uri = f"{input_['web_url']['scheme']}://{netloc}{port}{input_['web_url']['path']}"
    ip = input_["website"]["ip_service"]["ip_port"]["address"]["address"]

    # Code from https://github.com/Roadmaster/forcediphttpsadapter/blob/master/example.py
    url_parts = urlparse(uri)
    hostname = url_parts.netloc
    session = requests.Session()

    useragent = getenv("useragent", default="OpenKAT")

    if url_parts.scheme == "https":
        # Adapter is available, use it regardless of Python version
        base_url = urlunsplit((url_parts.scheme, url_parts.netloc, "", "", ""))
        session.mount(base_url, ForcedIPHTTPSAdapter(dest_ip=ip))
    else:
        # Fall back to old hack-ip-into-url behavior, for either https with no adapter, or http.
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

    body_mimetypes = {"openkat-http/body"}
    try:
        response = session.get(
            uri,
            headers={"Host": hostname, "User-Agent": useragent},
            verify=False,
            allow_redirects=False,
        )

    except requests.exceptions.RequestException as request_error:
        return [({"openkat-http/error"}, str(request_error))]

    if "content-type" in response.headers:
        content_type = response.headers.get("content-type")
        body_mimetypes.add(content_type)

        # Pick up the content type for the body from the server and split away encodings to make normalization easier
        content_type = content_type.split(";")
        body_mimetypes.add(content_type[0])

    return [
        ({"openkat-http/full"}, "%s\n\n%s" % (response.headers, response.content)),
        ({"openkat-http/headers"}, json.dumps(dict(response.headers))),
        (body_mimetypes, response.content),
    ]
