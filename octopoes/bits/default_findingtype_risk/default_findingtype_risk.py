from collections.abc import Iterator

from octopoes.models import OOI
from octopoes.models.ooi.findings import FindingType, RiskLevelSeverity


def run(input_ooi: FindingType, additional_oois: list, config: dict[str, str]) -> Iterator[OOI]:
    value_set = False
    if not input_ooi.risk_severity:
        input_ooi.risk_severity = RiskLevelSeverity.PENDING
        value_set = True
    if not input_ooi.risk_score:
        input_ooi.risk_score = 0
        value_set = True
    if value_set:
        yield input_ooi
