from typing import Dict, Iterator, List

import tldextract

from octopoes.models import OOI
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.email_security import DMARCTXTRecord
from octopoes.models.ooi.findings import Finding, KATFindingType


def run(input_ooi: Hostname, additional_oois: List[DMARCTXTRecord], config: Dict[str, str]) -> Iterator[OOI]:
    # only report finding when there is no DMARC record
    if (
        not tldextract.extract(input_ooi.name).subdomain
        and tldextract.extract(input_ooi.name).domain
        and not additional_oois
    ):
        ft = KATFindingType(id="KAT-NO-DMARC")
        yield ft
        yield Finding(
            ooi=input_ooi.reference,
            finding_type=ft.reference,
            description="This hostname does not have a DMARC record",
        )
