from reports.report_types.dns_report.report import DNSReport

from octopoes.models.tree import ReferenceTree


def test_dns_report_no_findings_no_dns_records(
    mock_octopoes_api_connector, valid_time, hostname, tree_data_no_findings
):
    mock_octopoes_api_connector.oois = {
        hostname.reference: hostname,
    }

    mock_octopoes_api_connector.tree = {
        hostname.reference: ReferenceTree.model_validate(tree_data_no_findings),
    }

    report = DNSReport(mock_octopoes_api_connector)
    data = report.generate_data(str(hostname.reference), valid_time)

    assert data["records"] == []
    assert data["security"]["spf"] is True
    assert data["security"]["dkim"] is True
    assert data["security"]["dmarc"] is True
    assert data["security"]["dnssec"] is True
    assert data["security"]["caa"] is True


def test_dns_report_all_findings_no_dns_records(
    mock_octopoes_api_connector, valid_time, hostname, tree_data_dns_findings
):
    mock_octopoes_api_connector.oois = {
        hostname.reference: hostname,
    }

    mock_octopoes_api_connector.tree = {
        hostname.reference: ReferenceTree.model_validate(tree_data_dns_findings),
    }

    report = DNSReport(mock_octopoes_api_connector)
    data = report.generate_data(str(hostname.reference), valid_time)

    assert data["records"] == []
    assert data["security"]["spf"] is False
    assert data["security"]["dkim"] is False
    assert data["security"]["dmarc"] is False
    assert data["security"]["dnssec"] is False
    assert data["security"]["caa"] is False
