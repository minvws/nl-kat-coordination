from typing import List, Iterator, Union

from octopoes.models import OOI
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.findings import KATFindingType, Finding
from octopoes.models.ooi.web import HTTPHeaderHostname
from octopoes.models.types import NXDOMAIN


def run(
    input_ooi: Hostname,
    additional_oois: List[Union[NXDOMAIN, HTTPHeaderHostname]],
) -> Iterator[OOI]:

    hostname_exists = True
    headers = []
    for ooi in additional_oois:
        if isinstance(ooi, NXDOMAIN):
            hostname_exists = False
        if isinstance(ooi, HTTPHeaderHostname):
            headers.append(ooi)

    if not hostname_exists:
        ft = KATFindingType(id="KAT-NXDOMAIN-HEADER")
        yield ft
        for header in headers:
            yield Finding(
                ooi=header.reference,
                finding_type=ft.reference,
                description="The hostname in the HTTP header does not exist",
            )
