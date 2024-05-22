from collections.abc import Iterable

from boefjes.job_models import NormalizerOutput
from octopoes.models import Reference
from octopoes.models.ooi.findings import Finding, KATFindingType


def run(input_ooi: dict, raw: bytes) -> Iterable[NormalizerOutput]:
    result = raw.decode()

    ooi_ref = Reference.from_str(input_ooi["primary_key"])

    for result_line in reversed(result.splitlines()):
        if not result_line.startswith(";"):
            break

    # [S] self sig OK; [B] bogus; [T] trusted; [U] unsigned
    if result_line.startswith("[U]"):
        ft = KATFindingType(id="KAT-NO-DNSSEC")
        finding = Finding(
            finding_type=ft.reference,
            ooi=ooi_ref,
            description=f"Domain {ooi_ref.human_readable} is not signed with DNSSEC.",
        )
        yield ft
        yield finding
    elif result_line.startswith("[S]") or result_line.startswith("[B]"):
        ft = KATFindingType(id="KAT-INVALID-DNSSEC")
        finding = Finding(
            finding_type=ft.reference,
            ooi=ooi_ref,
            description=f"Domain {ooi_ref.human_readable} is signed with an invalid DNSSEC.",
        )
        yield ft
        yield finding
    elif not result_line.startswith("[T]"):
        raise ValueError(f"Could not parse drill output: {result_line}")
