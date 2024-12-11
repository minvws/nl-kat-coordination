from bits.definitions import BitDefinition
from octopoes.models.ooi.findings import FindingType

BIT = BitDefinition(
    id="default-findingtype-risk",
    consumes=FindingType,
    parameters=[],
    module="bits.default_findingtype_risk.default_findingtype_risk",
    min_scan_level=0,
)
