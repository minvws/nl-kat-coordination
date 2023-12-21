from dataclasses import asdict
from octopoes.api.models import Declaration
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import Reference
from octopoes.models.ooi.findings import Finding

from reports.report_types.web_system_report.report import WebSystemReport

from tests.conftest import seed_system


def test_web_report(octopoes_api_connector: OctopoesAPIConnector, valid_time):
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
        "has_csp": True,
        "has_no_csp_vulnerabilities": True,
        "has_security_txt": False,
        "no_uncommon_ports": True,
        "offers_https": True,
        "redirects_http_https": True,
    }

    finding = Finding(
        finding_type=Reference.from_str("KATFindingType|KAT-NO-CSP"),
        ooi=Reference.from_str("HTTPResource|test|192.0.2.3|tcp|25|smtp|test|example.com|http|test|example.com|80|/"),
    )
    octopoes_api_connector.save_declaration(Declaration(ooi=finding, valid_time=valid_time))
    a = octopoes_api_connector.query(
        "Hostname.<hostname[is Website].<website[is HTTPResource].<ooi[is Finding].finding_type",
        valid_time,
        input_ooi,
    )

    assert report.generate_data(input_ooi, valid_time)["web_checks"].checks[0].has_csp is False
