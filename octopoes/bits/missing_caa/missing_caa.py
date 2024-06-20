from collections.abc import Iterator
from typing import Any

import tldextract

from octopoes.models import OOI
from octopoes.models.ooi.dns.records import NXDOMAIN, DNSCAARecord
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.findings import Finding, KATFindingType


def run(input_ooi: Hostname, additional_oois: list[DNSCAARecord | NXDOMAIN], config: dict[str, Any]) -> Iterator[OOI]:
    caa_records = [ooi for ooi in additional_oois if isinstance(ooi, DNSCAARecord)]
    nxdomains = (ooi for ooi in additional_oois if isinstance(ooi, NXDOMAIN))

    if any(nxdomains):
        return
    # only report finding when there is no SPF record
    if (
        not tldextract.extract(input_ooi.name).subdomain
        and tldextract.extract(input_ooi.name).domain
        and not caa_records
    ):
        ft = KATFindingType(id="KAT-NO-CAA")
        yield ft
        yield Finding(
            ooi=input_ooi.reference,
            finding_type=ft.reference,
            description="This hostname does not have a CAA record",
        )
