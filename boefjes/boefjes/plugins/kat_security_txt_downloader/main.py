import ipaddress
import json
from os import getenv
from typing import List, Tuple, Union

import requests
from forcediphttpsadapter.adapters import ForcedIPHTTPSAdapter
from requests import Session

from boefjes.job_models import BoefjeMeta


def run(boefje_meta: BoefjeMeta) -> List[Tuple[set, Union[bytes, str]]]:
    input_ = boefje_meta.arguments["input"]
    netloc = input_["hostname"]["name"]
    scheme = input_["ip_service"]["service"]["name"]
    ip = input_["ip_service"]["ip_port"]["address"]["address"]

    useragent = getenv("USERAGENT", default="OpenKAT")
    session = requests.Session()

    results = {}

    for path in [".well-known/security.txt", "security.txt"]:
        uri = f"{scheme}://{netloc}/{path}"

        if scheme == "https":
            session.mount(uri, ForcedIPHTTPSAdapter(dest_ip=ip))
        else:
            addr = ipaddress.ip_address(ip)
            if addr.version == 6:
                # IPv6 addresses need to be wrapped in brackets
                netloc = f"[{ip}]"

            uri = f"{scheme}://{netloc}/{path}"

        response = do_request(netloc, session, uri, useragent)

        # if the response is 200, return the content
        if response.status_code == 200:
            results[path] = {"content": response.content.decode(), "url": response.url, "ip": ip}
        # if the response is 301, we need to follow the location header to the correct security txt,
        # we can not force the ip anymore
        elif response.status_code == 301:
            uri = response.headers["Location"]
            response = requests.get(uri, stream=True)
            ip = response.raw._connection.sock.getpeername()[0]
            results[path] = {
                "content": response.content.decode(),
                "url": response.url,
                "ip": str(ip),
            }
    return [(set(), json.dumps(results))]


def do_request(hostname: str, session: Session, uri: str, useragent: str):
    response = session.get(
        uri,
        headers={"Host": hostname, "User-Agent": useragent},
        verify=False,
        allow_redirects=False,
    )

    return response
