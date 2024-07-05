import json
from collections.abc import Iterable

from boefjes.job_models import NormalizerOutput
from octopoes.models import Reference
from octopoes.models.ooi.findings import CVEFindingType, Finding


def run(input_ooi: dict, raw: bytes) -> Iterable[NormalizerOutput]:
    ooi = Reference.from_str(input_ooi["primary_key"])

    results = json.loads(raw)

    if results["status"] == "vulnerable":
        finding_type = CVEFindingType(id="CVE-2024-6387")
        finding = Finding(
            finding_type=finding_type.reference,
            ooi=ooi,
            description="Service is most likely vulnerable to CVE-2024-6387",
        )
        yield finding_type
        yield finding
