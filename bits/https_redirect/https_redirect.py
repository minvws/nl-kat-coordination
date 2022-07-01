from typing import List, Iterator, Union
from octopoes.models import OOI
from octopoes.models.ooi.findings import KATFindingType, Finding
from octopoes.models.ooi.network import IPPort, IPAddress
from octopoes.models.ooi.web import Website, WebURL, HTTPResource, HTTPHeader, HostnameHTTPURL


def run(
    input_ooi: HostnameHTTPURL,
    additional_oois: List[HTTPHeader],
) -> Iterator[OOI]:

    header_keys = [header.key.lower() for header in additional_oois if isinstance(header, HTTPHeader)]

    # only check for http urls
    if input_ooi.scheme.value != "http" or not header_keys:
        return

    if "location" not in header_keys:
        ft = KATFindingType(id="KAT-HTTPS-REDIRECT")
        yield Finding(
            ooi=input_ooi.reference, finding_type=ft.reference, description="This HTTP URL does not redirect to HTTPS"
        )
