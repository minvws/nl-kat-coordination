from typing import Iterator

from octopoes.models import OOI, Reference
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.network import Network

from octopoes.models.ooi.web import RawCookie, HTTPHeader


def run(
    input_ooi: HTTPHeader,
    additional_oois,
) -> Iterator[OOI]:
    if input_ooi.key.lower() == "set-cookie":
        domain = Hostname(
            name=input_ooi.resource.tokenized.website.hostname.name,
            network=Network(name=input_ooi.resource.tokenized.website.hostname.network.name).reference,
        )
        yield RawCookie(
            raw=input_ooi.value,
            response_domain=domain.reference,
        )
