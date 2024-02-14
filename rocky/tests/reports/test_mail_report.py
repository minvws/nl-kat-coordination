from reports.report_types.mail_report.report import MailReport


def test_mail_report_no_findings(mock_octopoes_api_connector, valid_time, hostname):
    mock_octopoes_api_connector.oois = {
        hostname.reference: hostname,
    }
    mock_octopoes_api_connector.queries = {
        "Hostname.<ooi[is Finding].finding_type": {
            hostname.reference: [],
        },
    }

    report = MailReport(mock_octopoes_api_connector)

    data = report.generate_data(str(hostname.reference), valid_time)

    assert len(data["finding_types"]) == 1
    assert data["number_of_hostnames"] == 1
    assert data["number_of_spf"] == 1
    assert data["number_of_dkim"] == 1
    assert data["number_of_dmarc"] == 1
