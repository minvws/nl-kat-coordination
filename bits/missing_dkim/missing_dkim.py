from typing import Iterator, List

from octopoes.models import OOI
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.email_security import DKIMExists

import tldextract

from octopoes.models.ooi.findings import KATFindingType, Finding


def run(
    input_ooi: Hostname,
    additional_oois: List[DKIMExists],
) -> Iterator[OOI]:

    if input_ooi.name == input_ooi.fqdn.tokenized.name and not tldextract.extract(input_ooi.name).subdomain:
        if not additional_oois:
            ft = KATFindingType(id="KAT-NO-DKIM")
            yield ft
            yield Finding(
                ooi=input_ooi.reference,
                finding_type=ft.reference,
                description="This hostname does not support DKIM records",
            )
