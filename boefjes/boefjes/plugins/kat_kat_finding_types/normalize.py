import json
import logging
from typing import Iterable, Union

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI
from octopoes.models.ooi.findings import KATFindingType, RiskLevelSeverity

logger = logging.getLogger(__name__)


SEVERITY_SCORE_LOOKUP = {
    RiskLevelSeverity.CRITICAL: 10.0,
    RiskLevelSeverity.HIGH: 8.9,
    RiskLevelSeverity.MEDIUM: 6.9,
    RiskLevelSeverity.LOW: 3.9,
    RiskLevelSeverity.RECOMMENDATION: 0.0,
}


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterable[OOI]:
    kat_finding_type_id = normalizer_meta.raw_data.boefje_meta.arguments["input"]["id"]
    data = json.loads(raw)

    finding_type_information = data[kat_finding_type_id]
    logger.info(finding_type_information["risk"].lower())
    risk_severity = RiskLevelSeverity(finding_type_information["risk"].lower())

    risk_score = SEVERITY_SCORE_LOOKUP[risk_severity]

    yield {
        "type": "declaration",
        "ooi": KATFindingType(
            id=kat_finding_type_id,
            description=finding_type_information.get("description", None),
            source=finding_type_information.get("source", None),
            impact=finding_type_information.get("impact", None),
            recommendation=finding_type_information.get("recommendation", None),
            risk_severity=risk_severity,
            risk_score=risk_score,
        ).dict(),
    }
