from typing import Iterable

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI, Reference
from octopoes.models.ooi.findings import CVEFindingType, Finding


def run(normalizer_meta: NormalizerMeta, raw: bytes) -> Iterable[OOI]:
    reference = Reference.from_str(normalizer_meta.raw_data.boefje_meta.input_ooi)

    if "SAFE" not in raw.decode().split()[1]:  # first line is header, second line should have answers
        finding_type = CVEFindingType(id="CVE-2023-44487")
        finding = Finding(
            finding_type=finding_type.reference,
            ooi=reference,
            description="Service is most likely vulnerable to CVE-2023-44487",
        )
        yield finding_type
        yield finding
