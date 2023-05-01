from typing import Iterator, List

import tldextract

from octopoes.models import OOI
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.email_security import DKIMExists
from octopoes.models.ooi.findings import Finding, KATFindingType


def run(
    input_ooi: Hostname,
    additional_oois: List[DKIMExists],
) -> Iterator[OOI]:
    if (
        # don't report on findings on subdomains because it's not needed on subdomains
        not tldextract.extract(input_ooi.name).subdomain
        # don't report on findings on tlds
        and tldextract.extract(input_ooi.name).domain
    ) and not additional_oois:
        ft = KATFindingType(id="KAT-NO-DKIM")
        yield ft
        yield Finding(
            ooi=input_ooi.reference,
            finding_type=ft.reference,
            description="This hostname does not support DKIM records",
        )
