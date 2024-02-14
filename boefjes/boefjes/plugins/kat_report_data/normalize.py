from collections.abc import Iterable

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI
from octopoes.models.ooi.reports import ReportData


def run(normalizer_meta: NormalizerMeta, raw: bytes | str) -> Iterable[OOI]:
    ooi = ReportData.model_validate_json(raw)
    yield {
        "type": "declaration",
        "ooi": ooi.dict(),
    }
