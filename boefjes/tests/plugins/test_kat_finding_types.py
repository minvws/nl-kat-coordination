import json
import logging

from boefjes.normalizer_models import NormalizerAffirmation
from boefjes.plugins.kat_kat_finding_types.normalize import run
from octopoes.models.ooi.findings import KATFindingType, RiskLevelSeverity


def test_kat_finding_types_unknown_id_does_not_crash():
    # Ids minted by bits (e.g. KAT-HTTPS-NOT-AVAILABLE) can be absent from the
    # static catalog. data[id] then raised KeyError, failing hydration for every
    # finding of this type.
    oois = list(run({"id": "KAT-HTTPS-NOT-AVAILABLE"}, json.dumps({}).encode()))

    assert oois == [
        NormalizerAffirmation(
            ooi=KATFindingType(id="KAT-HTTPS-NOT-AVAILABLE", risk_severity=RiskLevelSeverity.UNKNOWN, risk_score=None)
        )
    ]


def test_kat_finding_types_known_id():
    raw = json.dumps({"KAT-EXAMPLE": {"risk": "high", "name": "Example", "description": "An example."}}).encode()

    oois = list(run({"id": "KAT-EXAMPLE"}, raw))

    assert len(oois) == 1
    ooi = oois[0].ooi
    assert ooi.id == "KAT-EXAMPLE"
    assert ooi.risk_severity == RiskLevelSeverity.HIGH
    assert ooi.risk_score == 8.9
    assert ooi.name == "Example"


def test_kat_finding_types_missing_risk_key_does_not_crash():
    raw = json.dumps({"KAT-EXAMPLE": {"name": "Example"}}).encode()

    oois = list(run({"id": "KAT-EXAMPLE"}, raw))

    assert len(oois) == 1
    assert oois[0].ooi.risk_severity == RiskLevelSeverity.UNKNOWN
    assert oois[0].ooi.risk_score is None


def test_kat_finding_types_unrecognised_risk_falls_back_to_unknown(caplog):
    raw = json.dumps({"KAT-EXAMPLE": {"risk": "bogus", "name": "Example"}}).encode()

    with caplog.at_level(logging.WARNING):
        oois = list(run({"id": "KAT-EXAMPLE"}, raw))

    assert len(oois) == 1
    assert oois[0].ooi.risk_severity == RiskLevelSeverity.UNKNOWN
    assert oois[0].ooi.risk_score is None
    assert any("Unknown risk level" in record.message for record in caplog.records)


def test_kat_finding_types_groups():
    raw = json.dumps({"KAT-EXAMPLE": {"risk": "medium", "groups": ["http-security-headers"]}}).encode()
    ooi = list(run({"id": "KAT-EXAMPLE"}, raw))[0].ooi
    assert ooi.groups == ["http-security-headers"]


def test_group_validation():
    import pytest

    from boefjes.plugins.kat_kat_finding_types.main import validate_groups

    groups = {"web": {"parent": None}, "headers": {"parent": "web"}}
    validate_groups(groups, {"KAT-A": {"groups": ["headers"]}})
    with pytest.raises(ValueError):
        validate_groups(groups, {"KAT-A": {"groups": ["missing"]}})
    with pytest.raises(ValueError):
        validate_groups({"web": {"parent": "headers"}, "headers": {"parent": "web"}}, {})


def test_group_validation_rejects_malformed_parent():
    import pytest

    from boefjes.plugins.kat_kat_finding_types.main import validate_groups

    with pytest.raises(ValueError):
        validate_groups({"web": {"name": "Web", "parent": ["bad"]}}, {})


def test_group_validation_rejects_duplicate_membership():
    import pytest

    from boefjes.plugins.kat_kat_finding_types.main import validate_groups

    with pytest.raises(ValueError):
        validate_groups({"web": {"name": "Web"}}, {"KAT-A": {"groups": ["web", "web"]}})
