from dataclasses import asdict

from reports.report_types.web_system_report.report import WebSystemReport

from octopoes.api.models import Declaration
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import Reference
from octopoes.models.ooi.findings import Finding
from tests.conftest import seed_system


def test_web_report(octopoes_api_connector: OctopoesAPIConnector, valid_time):
    seed_system(octopoes_api_connector, valid_time)

    report = WebSystemReport(octopoes_api_connector)
    input_ooi = "Hostname|test|example.com"
    data = report.generate_data(input_ooi, valid_time)

    assert data["input_ooi"] == input_ooi
    assert len(data["finding_types"]) == 1
    assert len(data["web_checks"]) == 1

    assert asdict(data["web_checks"].checks[0]) == {
        "has_csp": True,
        "has_no_csp_vulnerabilities": True,
        "redirects_http_https": True,
        "offers_https": True,
        "has_security_txt": True,
        "no_uncommon_ports": True,
        "has_certificates": True,
        "certificates_not_expired": True,
        "certificates_not_expiring_soon": True,
    }

    finding = Finding(
        finding_type=Reference.from_str("KATFindingType|KAT-NO-CSP"),
        ooi=Reference.from_str("HTTPResource|test|192.0.2.3|tcp|25|smtp|test|example.com|http|test|example.com|80|/"),
    )
    octopoes_api_connector.save_declaration(Declaration(ooi=finding, valid_time=valid_time))
    checks = report.generate_data(input_ooi, valid_time)["web_checks"].checks
    assert checks[0].has_csp is False
    assert checks[0].has_no_csp_vulnerabilities is False

    finding = Finding(
        finding_type=Reference.from_str("KATFindingType|KAT-NO-CERTIFICATE"),
        ooi=Reference.from_str("Website|test|192.0.2.3|tcp|25|smtp|test|example.com"),
    )
    octopoes_api_connector.save_declaration(Declaration(ooi=finding, valid_time=valid_time))
    data = report.generate_data(input_ooi, valid_time)
    assert data["web_checks"].checks[0].offers_https is False

    assert len(data["finding_types"]) == 3
