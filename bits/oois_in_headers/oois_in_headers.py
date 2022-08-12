from typing import List, Iterator
import re

from pydantic import ValidationError

from octopoes.models import OOI
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.web import HTTPHeaderHostname
from octopoes.models.types import HTTPHeader, URL, Network, HTTPHeaderURL


def run(
    input_ooi: HTTPHeader,
    additional_oois: List,
) -> Iterator[OOI]:

    if input_ooi.key.lower() not in ["location", "content-security-policy"]:
        return

    network = Network(name="internet")

    urls_and_hostname = re.findall("(?:(?:https?|ftp):\/\/)?[\w/\-?=%.]+\.[\w/\-&?=%.]+", input_ooi.value)

    for object in urls_and_hostname:
        try:
            u = URL(raw=object, network=network.reference)
            yield u
            http_header_url = HTTPHeaderURL(header=input_ooi.reference, url=u.reference)
            yield http_header_url
        # some hostnames get classified as urls by the regex here, they need to be parsed by another bit
        except ValidationError:
            name = object if object[0] != "." else object[1:]
            h = Hostname(name=name, network=network.reference)
            yield h
            http_header_hostname = HTTPHeaderHostname(header=input_ooi.reference, hostname=h.reference)
            yield http_header_hostname
