from reports.report_types.findings_report.report import FindingsReport

from octopoes.models.tree import ReferenceTree


def test_findings_report_(mock_octopoes_api_connector, valid_time, hostname, tree_data, finding_types):
    mock_octopoes_api_connector.oois = {
        hostname.reference: hostname,
        finding_types[0].reference: finding_types[0],
    }

    mock_octopoes_api_connector.tree = {
        hostname.reference: ReferenceTree.model_validate(tree_data),
    }

    report = FindingsReport(mock_octopoes_api_connector)
    data = report.generate_data(str(hostname.reference), valid_time)

    assert len(data["finding_types"]) == 1
    assert data["summary"]["total_by_severity"]["high"] == 0
    assert data["summary"]["total_by_severity"]["critical"] == 1
    assert data["summary"]["total_by_severity_per_finding_type"]["high"] == 0
    assert data["summary"]["total_by_severity_per_finding_type"]["critical"] == 1
    assert data["summary"]["total_occurrences"] == 1
