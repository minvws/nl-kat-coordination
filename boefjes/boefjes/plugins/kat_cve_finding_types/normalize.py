import json
import logging
from typing import Iterable, Union

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI
from octopoes.models.ooi.findings import CVEFindingType, RiskLevelSeverity

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
    cve_finding_type_id = normalizer_meta.raw_data.boefje_meta.arguments["input"]["id"]
    data = json.loads(raw)

    descriptions = data["cve"]["descriptions"]
    english_description = [description for description in descriptions if description["lang"] == "en"][0]

    if not data["cve"]["metrics"]:
        risk_severity = RiskLevelSeverity.UNKNOWN
        risk_score = None
    else:
        metrics = data["cve"]["metrics"]
        if "cvssMetricV31" in metrics:
            cvss = metrics["cvssMetricV31"]
        elif "cvssMetricV30" in metrics:
            cvss = metrics["cvssMetricV30"]
        else:
            cvss = metrics["cvssMetricV2"]

        for item in cvss:
            if item["type"] == "Primary":
                risk_score = item["cvssData"]["baseScore"]
                break
        else:
            risk_score = cvss[0]["cvssData"]["baseScore"]
        risk_severity = get_risk_level(risk_score)

    yield CVEFindingType(
        id=cve_finding_type_id,
        description=english_description["value"],
        source=f"https://cve.circl.lu/cve/{cve_finding_type_id}",
        risk_severity=risk_severity,
        risk_score=risk_score,
    )
