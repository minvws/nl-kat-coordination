import json
import logging
from typing import Iterable, Union

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI
from octopoes.models.ooi.findings import CVEFindingType, RiskLevelSeverity

logger = logging.getLogger(__name__)


SEVERITY_SCORE_LOOKUP = {
    RiskLevelSeverity.CRITICAL: 10.0,
    RiskLevelSeverity.HIGH: 8.9,
    RiskLevelSeverity.MEDIUM: 6.9,
    RiskLevelSeverity.LOW: 3.9,
    RiskLevelSeverity.RECOMMENDATION: 0.0,
}


def get_risk_level(severity_score):
    for risk_level, score in SEVERITY_SCORE_LOOKUP.items():
        if severity_score >= score:
            return risk_level
    return None


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterable[OOI]:
    cve_finding_type_id = normalizer_meta.raw_data.boefje_meta.arguments["input"]["id"]
    data = json.loads(raw)

    descriptions = data["cve"]["description"]["description_data"]
    english_description = [description for description in descriptions if description["lang"] == "en"][0]

    if data["impact"] == {}:
        risk_severity = RiskLevelSeverity.UNKNOWN
        risk_score = None
    else:
        try:
            risk_score = data["impact"]["baseMetricV3"]["cvssV3"]["baseScore"]
        except KeyError:
            risk_score = data["impact"]["baseMetricV2"]["cvssV2"]["baseScore"]
        risk_severity = get_risk_level(risk_score)

    yield CVEFindingType(
        id=cve_finding_type_id,
        description=english_description["value"],
        source=f"https://cve.circl.lu/cve/{cve_finding_type_id}",
        risk_severity=risk_severity,
        risk_score=risk_score,
    )
