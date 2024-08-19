from collections.abc import Iterable

from boefjes.job_models import NormalizerOutput
from octopoes.models import Reference
from octopoes.models.ooi.findings import CVEFindingType, Finding


def run(input_ooi: dict, raw: bytes) -> Iterable[NormalizerOutput]:
    ooi = Reference.from_str(input_ooi["primary_key"])
    cve_id = raw.decode()

    if cve_id:
        finding_type = CVEFindingType(id=cve_id)
        finding = Finding(
            finding_type=finding_type.reference,
            ooi=ooi,
            description=f"CVE {cve_id} is found on this OOI",
        )
        yield finding_type
        yield finding
