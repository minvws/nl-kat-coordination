import json
from collections.abc import Iterable
from ipaddress import IPv4Address

from boefjes.job_models import NormalizerOutput
from octopoes.models import Reference
from octopoes.models.ooi.findings import Finding, KATFindingType


def run(input_ooi: dict, raw: bytes) -> Iterable[NormalizerOutput]:
    results = json.loads(raw)
    ooi = Reference.from_str(input_ooi["primary_key"])

    address = IPv4Address(ooi.tokenized.address)

    # if the address is private, we do not need a ROA
    if not address.is_private:
        if not results["exists"]:
            ft = KATFindingType(id="KAT-NO-RPKI")
            f = Finding(finding_type=ft.reference, ooi=ooi)
            yield ft
            yield f

        if results["invalid_bgp_entries"]:
            ft = KATFindingType(id="KAT-INVALID-RPKI")
            f = Finding(finding_type=ft.reference, ooi=ooi)
            yield ft
            yield f
