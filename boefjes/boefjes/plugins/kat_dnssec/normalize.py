import json
from collections.abc import Iterable

from boefjes.job_models import NormalizerOutput
from octopoes.models import Reference
from octopoes.models.ooi.findings import Finding, KATFindingType


def run(input_ooi: dict, raw: bytes) -> Iterable[NormalizerOutput]:
    result = json.loads(raw)

    ooi_ref = Reference.from_str(input_ooi["primary_key"])

    possible_errors: list[str] = [
        "Bogus DNSSEC signature",
        "DNSSEC signature not incepted yet",
        "Unknown cryptographic algorithm",
        "DNSSEC signature has expired",
    ]

    if "No trusted keys found in tree" in result and "No DNSSEC public key(s)" in result:
        ft = KATFindingType(id="KAT-NO-DNSSEC")
        finding = Finding(
            finding_type=ft.reference,
            ooi=ooi_ref,
            description=f"Domain {ooi_ref.human_readable} is not signed with DNSSEC.",
        )
        yield ft
        yield finding

    if "No trusted keys found in tree" in result and [error for error in possible_errors if error in result]:
        ft = KATFindingType(id="KAT-INVALID-DNSSEC")
        finding = Finding(
            finding_type=ft.reference,
            ooi=ooi_ref,
            description=f"Domain {ooi_ref.human_readable} is signed with an invalid DNSSEC.",
        )
        yield ft
        yield finding
