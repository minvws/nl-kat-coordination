from reports.report_types.tls_report.report import TLSReport

from octopoes.models.tree import ReferenceTree


def test_tls_report_no_suites_no_findings(mock_octopoes_api_connector, valid_time, ip_service, tree_data_no_findings):
    mock_octopoes_api_connector.tree = {
        ip_service.reference: ReferenceTree.model_validate(tree_data_no_findings),
    }

    report = TLSReport(mock_octopoes_api_connector)
    data = report.generate_data(str(ip_service.reference), valid_time)

    assert data["suites"] == {}
    assert data["findings"] == []
    assert data["suites_with_findings"] == []


def test_tls_report_multiple_findings_and_suites(
    mock_octopoes_api_connector,
    valid_time,
    ip_service,
    cipher_finding_type,
    cipher_finding_types,
    tree_data_tls_findings_and_suites,
):
    mock_octopoes_api_connector.oois = {
        ip_service.reference: ip_service,
        cipher_finding_types[0].reference: cipher_finding_types[0],
        cipher_finding_types[1].reference: cipher_finding_types[1],
        cipher_finding_type.reference: cipher_finding_type,
    }
    mock_octopoes_api_connector.tree = {
        ip_service.reference: ReferenceTree.model_validate(tree_data_tls_findings_and_suites),
    }

    report = TLSReport(mock_octopoes_api_connector)
    data = report.generate_data(str(ip_service.reference), valid_time)

    assert len(data["suites"]) == 1
    assert list(data["suites"].keys())[0] == "TLSv1"
    assert data["suites"]["TLSv1"][0]["cipher_suite_name"] == "ECDHE-RSA-AES128-SHA"
    assert data["suites"]["TLSv1"][1]["cipher_suite_name"] == "ECDHE-RSA-AES256-SHA"

    assert len(data["findings"]) == 3
    assert data["findings"][0].primary_key == "Finding|Network|testnetwork|KAT-0001"
    assert data["findings"][1].primary_key == "Finding|Network|testnetwork|KAT-0002"
    assert data["findings"][2].primary_key == "Finding|Network|testnetwork|KAT-0003"

    assert len(data["suites_with_findings"]) == 2
    assert data["suites_with_findings"][0] == "ECDHE-RSA-AES128-SHA"
    assert data["suites_with_findings"][1] == "ECDHE-RSA-AES256-SHA"
