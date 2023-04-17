from typing import Iterator, List

import tldextract

from octopoes.models import OOI
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.email_security import DNSSPFRecord
from octopoes.models.ooi.findings import Finding, KATFindingType


def run(
    input_ooi: Hostname,
    additional_oois: List[DNSSPFRecord],
) -> Iterator[OOI]:
    if (
        # don't report on findings on subdomains because it would generate too much noise
        not tldextract.extract(input_ooi.name).subdomain
        # don't report on findings on tlds
        and tldextract.extract(input_ooi.name).domain
    ):
        if not additional_oois:
            ft = KATFindingType(id="KAT-NO-SPF")
            yield ft
            yield Finding(
                ooi=input_ooi.reference,
                finding_type=ft.reference,
                description="This hostname does not have an SPF record",
            )
