from nibbles.default_findingtype_risk.default_findingtype_risk import nibble as run_default_findingtype_risk

from octopoes.models.ooi.findings import KATFindingType, RiskLevelSeverity


def test_default_findingtype_risk_pending():
    test_finding_type = KATFindingType(id="KAT-TEST")

    assert test_finding_type.risk_severity is None
    assert test_finding_type.risk_score is None

    results = list(run_default_findingtype_risk(test_finding_type, 0))

    expected_result = results[0]
    assert isinstance(expected_result, KATFindingType)
    assert expected_result.risk_severity == RiskLevelSeverity.PENDING, "Risk Severity None should default to pending"
    assert expected_result.risk_score == 0, "Risk Score None should default to 0"


def test_default_findingtype_risk_unkown():
    test_finding_type = KATFindingType(id="KAT-TEST", risk_severity=RiskLevelSeverity.UNKNOWN, risk_score=5)

    results = list(run_default_findingtype_risk(test_finding_type, 0))

    assert results == [], "Bit should not output anything when risk_severity or risk_score are set"
