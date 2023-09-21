import json
import logging
from typing import Iterable, Union

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI
from octopoes.models.ooi.findings import RiskLevelSeverity, SnykFindingType

logger = logging.getLogger(__name__)


SEVERITY_SCORE_LOOKUP = {
    RiskLevelSeverity.CRITICAL: 9.0,
    RiskLevelSeverity.HIGH: 7.0,
    RiskLevelSeverity.MEDIUM: 4.0,
    RiskLevelSeverity.LOW: 0.1,
    RiskLevelSeverity.RECOMMENDATION: 0.0,
}


def get_risk_level(severity_score):
    for risk_level, score in SEVERITY_SCORE_LOOKUP.items():
        if severity_score >= score:
            return risk_level
    return None


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterable[OOI]:
    snyk_finding_type_id = normalizer_meta.raw_data.boefje_meta.arguments["input"]["id"]
    data = json.loads(raw)

    risk_score = data.get("risk")
    risk_severity = get_risk_level(float(risk_score))

    yield SnykFindingType(
        id=snyk_finding_type_id,
        description=data.get("summary"),
        source=f"https://snyk.io/vuln/{snyk_finding_type_id}",
        risk_severity=risk_severity,
        risk_score=risk_score,
    )
