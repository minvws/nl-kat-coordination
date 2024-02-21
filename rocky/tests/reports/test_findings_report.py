from reports.report_types.findings_report.report import FindingsReport

from octopoes.models.tree import ReferenceTree


def test_findings_report_(mock_octopoes_api_connector, valid_time, hostname, tree_data, finding):
    mock_octopoes_api_connector.oois = {
        hostname.reference: hostname,
    }

    mock_octopoes_api_connector.tree = {
        hostname.reference: ReferenceTree.model_validate(tree_data),
    }

    mock_octopoes_api_connector.get = {
        hostname.reference: finding.finding_type,
    }

    report = FindingsReport(mock_octopoes_api_connector)

    data = report.generate_data(str(hostname.reference), valid_time)

    assert len(data["finding_types"]) == 1
    assert data["summary"]["total_by_sevirity"]["high"] == 1
    assert data["summary"]["total_by_sevirity_per_finding_type"]["high"] == 1
    assert data["summary"]["total_occurrences"] == 1
