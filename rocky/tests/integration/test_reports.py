from dataclasses import asdict

from reports.report_types.web_system_report.report import WebSystemReport

from tests.conftest import seed_system


def test_account_detail_perms(octopoes_api_connector, valid_time):
    seed_system(octopoes_api_connector, valid_time)

    report = WebSystemReport(octopoes_api_connector)
    input_ooi = "Hostname|test|example.com"
    data = report.generate_data(input_ooi, valid_time)

    assert "input_ooi" in data
    assert "web_checks" in data
    assert "finding_types" in data

    assert data["input_ooi"] == input_ooi
    assert len(data["web_checks"]) == 1
    assert asdict(data["web_checks"].checks[0]) == {
        "certificates_not_expired": True,
        "certificates_not_expiring_soon": True,
        "has_certificates": True,
        "has_csp": False,
        "has_no_csp_vulnerabilities": False,
        "has_security_txt": False,
        "no_uncommon_ports": True,
        "offers_https": True,
        "redirects_http_https": False,
    }
