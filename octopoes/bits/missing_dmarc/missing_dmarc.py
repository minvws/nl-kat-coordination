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

    if (
        # only report on findings on the fqdn because of double findings
        input_ooi.name == input_ooi.fqdn.tokenized.name
        # don't report on findings on subdomains because it's not needed on subdomains
        and not tldextract.extract(input_ooi.name).subdomain
        # don't report on findings on tlds
        and tldextract.extract(input_ooi.name).domain
    ):
        if not additional_oois:
            ft = KATFindingType(id="KAT-NO-DMARC")
            yield ft
            yield Finding(
                ooi=input_ooi.reference,
                finding_type=ft.reference,
                description="This hostname does not have a DMARC record",
            )
