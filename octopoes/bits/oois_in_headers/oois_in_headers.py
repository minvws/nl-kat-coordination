import re
from collections.abc import Iterator
from urllib.parse import urljoin, urlparse

from pydantic import ValidationError

from octopoes.models import OOI
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.web import HTTPHeaderHostname
from octopoes.models.types import URL, HTTPHeader, HTTPHeaderURL, Network


def is_url(input_str):
    result = urlparse(input_str)
    return bool(result.scheme)


def run(input_ooi: HTTPHeader, additional_oois: list, config: dict[str, str]) -> Iterator[OOI]:
    network = Network(name="internet")

    if input_ooi.key.lower() == "location":
        if is_url(input_ooi.value):
            u = URL(raw=input_ooi.value, network=network.reference)
        else:
            # url is not a url but a relative path
            http_url = input_ooi.reference.tokenized.resource.web_url
            # allow for ipaddress http urls
            netloc = http_url.netloc.name if "name" in http_url.netloc.root else http_url.netloc.address
            original_url = f"{http_url.scheme}://{netloc}{http_url.path}"
            u = URL(raw=urljoin(original_url, input_ooi.value), network=network.reference)
        yield u
        http_header_url = HTTPHeaderURL(header=input_ooi.reference, url=u.reference)
        yield http_header_url

    if input_ooi.key.lower() == "content-security-policy":
        urls_and_hostname = re.findall(r"(?:(?:https?|ftp):\/\/)?[\w/\-?=%.]+\.[\w/\-&?=%.]+", input_ooi.value)

        for url_or_hostname in urls_and_hostname:
            try:
                u = URL(raw=url_or_hostname, network=network.reference)
                yield u
                http_header_url = HTTPHeaderURL(header=input_ooi.reference, url=u.reference)
                yield http_header_url
            # some hostnames get classified as urls by the regex here, they need to be parsed by another bit
            except ValidationError:
                name = url_or_hostname if url_or_hostname[0] != "." else url_or_hostname[1:]
                h = Hostname(name=name, network=network.reference)
                yield h
                http_header_hostname = HTTPHeaderHostname(header=input_ooi.reference, hostname=h.reference)
                yield http_header_hostname
