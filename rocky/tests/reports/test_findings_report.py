from reports.report_types.findings_report.report import SOFTWARE_FINDINGS_PATH, FindingsReport

from octopoes.models.ooi.findings import CVEFindingType, Finding, RiskLevelSeverity
from octopoes.models.ooi.software import Software, SoftwareInstance
from octopoes.models.tree import ReferenceTree


def test_findings_report_no_findings(mock_octopoes_api_connector, valid_time, hostname, tree_data_no_findings):
    mock_octopoes_api_connector.oois = {hostname.reference: hostname}

    mock_octopoes_api_connector.tree = {hostname.reference: ReferenceTree.model_validate(tree_data_no_findings)}

    report = FindingsReport(mock_octopoes_api_connector)
    data = report.generate_data(str(hostname.reference), valid_time)

    assert data["summary"]["total_by_severity"]["critical"] == 0
    assert data["summary"]["total_by_severity_per_finding_type"]["critical"] == 0
    assert data["summary"]["total_finding_types"] == 0
    assert data["summary"]["total_occurrences"] == 0


def test_findings_report_two_findings_one_finding_type(
    mock_octopoes_api_connector, valid_time, hostname, tree_data_findings, finding_types
):
    mock_octopoes_api_connector.oois = {
        finding_types[0].reference: finding_types[0],
        finding_types[1].reference: finding_types[1],
    }

    # This tree data contains four OOIs, three of which are findings that contain two different finding_types.
    mock_octopoes_api_connector.tree = {hostname.reference: ReferenceTree.model_validate(tree_data_findings)}

    report = FindingsReport(mock_octopoes_api_connector)
    data = report.generate_data(str(hostname.reference), valid_time)

    assert data["finding_types"][0]["finding_type"] == finding_types[0]
    assert data["finding_types"][1]["finding_type"] == finding_types[1]
    assert data["summary"]["total_by_severity"]["critical"] == 3
    assert data["summary"]["total_by_severity_per_finding_type"]["critical"] == 2
    assert data["summary"]["total_finding_types"] == 2
    assert data["summary"]["total_occurrences"] == 3


def test_findings_report_includes_cve_bound_to_software(mock_octopoes_api_connector, valid_time, hostname):
    """A CVE hangs on the Software OOI, so the object tree never reaches it (#5321).

    The report has to walk the last two hops -- SoftwareInstance -> Software -> Finding -- itself.
    """
    software = Software(name="nginx", version="1.0")
    instance = SoftwareInstance(ooi=hostname.reference, software=software.reference)
    finding_type = CVEFindingType(id="CVE-2024-0001", risk_score=9.8, risk_severity=RiskLevelSeverity.CRITICAL)
    finding = Finding(finding_type=finding_type.reference, ooi=software.reference, description="")

    mock_octopoes_api_connector.oois = {finding_type.reference: finding_type}
    mock_octopoes_api_connector.tree = {
        hostname.reference: ReferenceTree.model_validate(
            {
                "root": {"reference": str(hostname.reference), "children": {}},
                "store": {str(instance.reference): instance.model_dump(mode="json")},
            }
        )
    }
    mock_octopoes_api_connector.queries = {SOFTWARE_FINDINGS_PATH: {str(instance.reference): [finding]}}

    report = FindingsReport(mock_octopoes_api_connector)
    data = report.generate_data(str(hostname.reference), valid_time)

    assert data["finding_types"][0]["finding_type"] == finding_type
    assert data["summary"]["total_occurrences"] == 1
    assert data["summary"]["total_by_severity"]["critical"] == 1
