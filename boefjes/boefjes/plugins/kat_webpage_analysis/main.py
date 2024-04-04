import ipaddress
import json
import mimetypes
from os import getenv
from urllib.parse import urlparse, urlunsplit

import requests
from forcediphttpsadapter.adapters import ForcedIPHTTPSAdapter
from requests import Session

from boefjes.job_models import BoefjeMeta

ALLOWED_CONTENT_TYPES = mimetypes.types_map.values()


def run(boefje_meta: BoefjeMeta) -> list[tuple[set, bytes | str]]:
    input_ = boefje_meta.arguments["input"]
    useragent = getenv("USERAGENT", default="OpenKAT")

    uri = get_uri(input_)
    ip = input_["website"]["ip_service"]["ip_port"]["address"]["address"]
    # Code from https://github.com/Roadmaster/forcediphttpsadapter/blob/master/example.py
    url_parts = urlparse(uri)
    hostname = url_parts.netloc
    session = requests.Session()

    if url_parts.scheme == "https":
        # Adapter is available, use it regardless of Python version
        base_url = urlunsplit((url_parts.scheme, url_parts.netloc, "", "", ""))
        session.mount(base_url, ForcedIPHTTPSAdapter(dest_ip=ip))
    else:
        # Fall back to old hack-ip-into-url behavior, for either https with no adapter, or http.
        if ip:
            try:
                addr = ipaddress.ip_address(ip)
            except ValueError:
                # Not a valid IP address, so don't try to hack it into the URL
                pass
            else:
                url_parts = url_parts._replace(netloc=f"[{ip}]") if addr.version == 6 else url_parts._replace(netloc=ip)

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
        response = do_request(hostname, session, uri, useragent)
    except requests.exceptions.RequestException as request_error:
        return [({"openkat-http/error"}, str(request_error))]

    if "content-type" in response.headers:
        content_type = response.headers["content-type"]

        if content_type in ALLOWED_CONTENT_TYPES:
            body_mimetypes.add(content_type)

        # Pick up the content type for the body from the server and split away encodings to make normalization easier
        content_type = content_type.split(";")
        if content_type[0] in ALLOWED_CONTENT_TYPES:
            body_mimetypes.add(content_type[0])

    # in case of a full response object, we hexdump to avoid issues with binary data or different encoding
    response_dump = json.dumps(create_response_object(response))

    return [
        ({"openkat-http/response"}, response_dump.encode() + b"\n\n" + response.content),
        ({"openkat-http/headers"}, json.dumps(dict(response.headers))),
        (body_mimetypes, response.content),
    ]


# todo: perhaps also implement response.history?
def create_response_object(response: requests.Response) -> dict:
    return {
        "response": {
            "url": response.url,
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "cookies": dict(response.cookies),
            "is_redirect": response.is_redirect,
            "encoding": response.encoding,
        },
        "request": {
            "url": response.request.url,
            "method": response.request.method,
            "headers": dict(response.request.headers),
        },
    }


def do_request(hostname: str, session: Session, uri: str, useragent: str):
    response = session.get(
        uri,
        headers={"Host": hostname, "User-Agent": useragent},
        verify=False,
        allow_redirects=False,
    )

    return response


def get_uri(input_: dict) -> str:
    port = f":{input_['web_url']['port']}"
    netloc = (
        input_["web_url"]["netloc"]["address"]
        if "address" in input_["web_url"]["netloc"]
        else input_["web_url"]["netloc"]["name"]
    )
    uri = f"{input_['web_url']['scheme']}://{netloc}{port}{input_['web_url']['path']}"

    return uri
