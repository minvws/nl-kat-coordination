from typing import Iterator, List

from octopoes.models import OOI
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.email_security import DMARCTXTRecord

import tldextract

from octopoes.models.ooi.findings import KATFindingType, Finding


def run(
    input_ooi: Hostname,
    additional_oois: List[DMARCTXTRecord],
) -> Iterator[OOI]:

    # Only needs DMARC when it is the fqdn and not a subdomain
    if input_ooi.name == input_ooi.fqdn.tokenized.name and not tldextract.extract(input_ooi.name).subdomain:
        if not additional_oois:
            ft = KATFindingType(id="KAT-NO-DMARC")
            yield ft
            yield Finding(
                ooi=input_ooi.reference,
                finding_type=ft.reference,
                description="This hostname does not have a DMARC record",
            )
