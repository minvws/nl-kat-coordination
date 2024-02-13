import json
import logging
from typing import Iterable, Union

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI
from octopoes.models.ooi.findings import CWEFindingType, RiskLevelSeverity

logger = logging.getLogger(__name__)


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterable[OOI]:
    cwe_finding_type_id = normalizer_meta.raw_data.boefje_meta.arguments["input"]["id"]
    data = json.loads(raw)

    risk_severity = RiskLevelSeverity.UNKNOWN
    risk_score = None

    yield {
        "type": "affirmation",
        "ooi": CWEFindingType(
            id=cwe_finding_type_id,
            description=f"{data['name']} - {data['description']}",
            source=f'https://cwe.mitre.org/data/definitions/{cwe_finding_type_id.split("-")[1]}.html',
            risk_severity=risk_severity,
            risk_score=risk_score,
        ).dict(),
    }
