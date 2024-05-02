import ipaddress
import json
from os import getenv

import requests
from forcediphttpsadapter.adapters import ForcedIPHTTPSAdapter
from requests import Session

from boefjes.job_models import BoefjeMeta

DEFAULT_TIMEOUT = 30

def run(boefje_meta: BoefjeMeta) -> list[tuple[set, bytes | str]]:
    input_ = boefje_meta.arguments["input"]
    netloc = input_["hostname"]["name"]
    scheme = input_["ip_service"]["service"]["name"]
    ip = input_["ip_service"]["ip_port"]["address"]["address"]

    useragent = getenv("USERAGENT", default="OpenKAT")
    
    try:
        timeout = int(getenv("TIMEOUT", default=DEFAULT_TIMEOUT))
    except ValueError:
        timeout = DEFAULT_TIMEOUT

    session = requests.Session()

    results = {}

    for path in [".well-known/security.txt", "security.txt"]:
        uri = f"{scheme}://{netloc}/{path}"

        if scheme == "https":
            session.mount(uri, ForcedIPHTTPSAdapter(dest_ip=ip))
        else:
            addr = ipaddress.ip_address(ip)
            iploc = f"[{ip}]" if addr.version == 6 else ip
            uri = f"{scheme}://{iploc}/{path}"

        response = do_request(netloc, session, uri, useragent, timeout)

        # if the response is 200, return the content
        if response.status_code == 200:
            results[path] = {"content": response.content.decode(), "url": response.url, "ip": ip, "status": 200}
        # if the response is 301, we need to follow the location header to the correct security txt,
        # we can not force the ip anymore because we dont know it yet.
        # TODO return a redirected URL and have OpenKAT figure out if we want to follow this.
        elif response.status_code in [301, 302, 307, 308]:
            uri = response.headers["Location"]
            response = requests.get(uri, stream=True, timeout=timeout, verify=False)  # noqa: S501
            ip = response.raw._connection.sock.getpeername()[0]
            results[path] = {
                "content": response.content.decode(),
                "url": response.url,
                "original_url": uri,
                "ip": str(ip),
                "status": response.status_code,
            }
        else:
            results[path] = {"content": response.content.decode(), "url": None, "ip": None, "status": response.status_code}
    return [(set(), json.dumps(results))]


def do_request(hostname: str, session: Session, uri: str, useragent: str, timeout: int):
    response = session.get(
        uri,
        headers={"Host": hostname, "User-Agent": useragent},
        timeout=timeout,
        verify=False,
        allow_redirects=False,
    )

    return response
