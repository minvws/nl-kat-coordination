from typing import Dict, Iterator, List

from octopoes.models import OOI
from octopoes.models.ooi.findings import Finding, KATFindingType
from octopoes.models.ooi.web import HostnameHTTPURL, HTTPHeader


def run(input_ooi: HostnameHTTPURL, additional_oois: List[HTTPHeader], config: Dict[str, str]) -> Iterator[OOI]:
    header_keys = [header.key.lower() for header in additional_oois if isinstance(header, HTTPHeader)]

    # only check for http urls
    if input_ooi.scheme.value != "http" or not header_keys:
        return

    if "location" not in header_keys:
        ft = KATFindingType(id="KAT-NO-HTTPS-REDIRECT")
        yield ft
        yield Finding(
            ooi=input_ooi.reference,
            finding_type=ft.reference,
            description="This HTTP URL may not redirect to HTTPS; 'location' was not found in HTTPHeader.",
        )
