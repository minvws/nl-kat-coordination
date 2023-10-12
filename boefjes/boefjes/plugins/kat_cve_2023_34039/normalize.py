from typing import Iterable

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI, Reference
from octopoes.models.ooi.findings import CVEFindingType, Finding


def run(normalizer_meta: NormalizerMeta, raw: str) -> Iterable[OOI]:
    ooi = Reference.from_str(normalizer_meta.raw_data.boefje_meta.input_ooi)

    if "is allowed access to vRealize Network Insight " in raw:
        finding_type = CVEFindingType(id="CVE-2023-34039")
        finding = Finding(
            finding_type=finding_type.reference,
            ooi=ooi,
            description="Service is most likely vulnerable to CVE-2023-34039",
        )
        yield finding_type
        yield finding
