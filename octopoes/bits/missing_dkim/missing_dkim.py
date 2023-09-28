from typing import Dict, Iterator, List, Union

import tldextract

from octopoes.models import OOI
from octopoes.models.ooi.dns.records import NXDOMAIN
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.email_security import DKIMExists
from octopoes.models.ooi.findings import Finding, KATFindingType


def run(
    input_ooi: Hostname, additional_oois: List[Union[DKIMExists, NXDOMAIN]], config: Dict[str, str]
) -> Iterator[OOI]:
    dkim_exists = [ooi for ooi in additional_oois if isinstance(ooi, DKIMExists)]
    nxdomains = (ooi for ooi in additional_oois if isinstance(ooi, NXDOMAIN))

    if any(nxdomains):
        return

    # only report finding when there is no DKIM record
    if (
        not tldextract.extract(input_ooi.name).subdomain
        and tldextract.extract(input_ooi.name).domain
        and not dkim_exists
    ):
        ft = KATFindingType(id="KAT-NO-DKIM")
        yield ft
        yield Finding(
            ooi=input_ooi.reference,
            finding_type=ft.reference,
            description="This hostname does not support DKIM records",
        )
