import hashlib
import json
import logging
from typing import Dict, Iterable, List, Union

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI
from octopoes.models.ooi.findings import RetireJSFindingType, RiskLevelSeverity

logger = logging.getLogger(__name__)


SEVERITY_SCORE_LOOKUP = {
    RiskLevelSeverity.CRITICAL: 10.0,
    RiskLevelSeverity.HIGH: 8.9,
    RiskLevelSeverity.MEDIUM: 6.9,
    RiskLevelSeverity.LOW: 3.9,
    RiskLevelSeverity.RECOMMENDATION: 0.0,
}


def _hash_identifiers(identifiers: Dict[str, Union[str, List[str]]]) -> str:
    pre_hash = ""
    for identifier in identifiers.values():
        pre_hash += "".join(identifier)
    return hashlib.sha1(pre_hash.encode()).hexdigest()[:4]


def _create_description(finding: dict) -> str:
    if "summary" in finding["identifiers"]:
        description = finding["identifiers"]["summary"] + ". More information at: "
    else:
        description = "No summary available. Find more information at: "

    info = finding["info"]
    description += ", ".join(info[:-1])
    if len(info) > 1:
        description += " or " + info[-1]
    else:
        description += info[0]

    return description


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterable[OOI]:
    retirejs_finding_type_id = normalizer_meta.raw_data.boefje_meta.arguments["input"]["id"]
    data = json.loads(raw)

    _, name, hashed_id = retirejs_finding_type_id.split("-")

    software = [
        brand
        for brand in data
        if name == brand.lower().replace(" ", "").replace("_", "").replace("-", "").replace(".", "")
    ][0]
    issues = data[software]["vulnerabilities"]

    finding = [issue for issue in issues if _hash_identifiers(issue["identifiers"]) == hashed_id]

    if not finding:
        return

    risk_severity = RiskLevelSeverity(finding[0]["severity"].lower())
    risk_score = SEVERITY_SCORE_LOOKUP[risk_severity]

    yield {
        "type": "affirmation",
        "ooi": RetireJSFindingType(
            id=retirejs_finding_type_id,
            description=_create_description(finding[0]),
            risk_severity=risk_severity,
            risk_score=risk_score,
        ).dict(),
    }
