from dataclasses import asdict

from reports.report_types.aggregate_organisation_report.report import AggregateOrganisationReport, aggregate_reports
from reports.report_types.systems_report.report import SystemReport, SystemType
from reports.report_types.web_system_report.report import WebSystemReport

from octopoes.api.models import Declaration
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import Reference
from octopoes.models.ooi.findings import Finding, KATFindingType, RiskLevelSeverity
from tests.integration.conftest import seed_system


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


def test_system_report(octopoes_api_connector: OctopoesAPIConnector, valid_time):
    seed_system(octopoes_api_connector, valid_time)

    report = SystemReport(octopoes_api_connector)
    input_ooi = "Hostname|test|example.com"
    data = report.generate_data(input_ooi, valid_time)

    assert data["input_ooi"] == input_ooi
    assert data["summary"] == {
        "total_domains": 10,  # TODO: this is not deduplicated, should it be?
        "total_systems": 2,
    }
    assert data["services"] == {
        "IPAddressV4|test|192.0.2.3": {
            "hostnames": [
                "Hostname|test|a.example.com",
                "Hostname|test|b.example.com",
                "Hostname|test|c.example.com",
                "Hostname|test|d.example.com",
                "Hostname|test|e.example.com",
                "Hostname|test|example.com",
            ],
            "services": [SystemType.DICOM, SystemType.MAIL, SystemType.OTHER, SystemType.WEB],
        },
        "IPAddressV6|test|3e4d:64a2:cb49:bd48:a1ba:def3:d15d:9230": {
            "hostnames": [
                "Hostname|test|c.example.com",
                "Hostname|test|d.example.com",
                "Hostname|test|example.com",
                "Hostname|test|f.example.com",
            ],
            "services": [SystemType.WEB],
        },
    }


def test_aggregate_report(octopoes_api_connector: OctopoesAPIConnector, valid_time):
    seed_system(octopoes_api_connector, valid_time)

    reports = AggregateOrganisationReport.reports["required"] + AggregateOrganisationReport.reports["optional"]
    report_types = [{"id": x.id, "name": "", "description": ""} for x in reports]
    _, data, _ = aggregate_reports(octopoes_api_connector, ["Hostname|test|example.com"], report_types, valid_time)

    v4_test_hostnames = [
        "Hostname|test|a.example.com",
        "Hostname|test|b.example.com",
        "Hostname|test|c.example.com",
        "Hostname|test|d.example.com",
        "Hostname|test|e.example.com",
        "Hostname|test|example.com",
    ]

    assert data["systems"]["services"] == {
        "IPAddressV4|test|192.0.2.3": {
            "hostnames": v4_test_hostnames,
            "services": [SystemType.DICOM, SystemType.MAIL, SystemType.OTHER, SystemType.WEB],
        },
        "IPAddressV6|test|3e4d:64a2:cb49:bd48:a1ba:def3:d15d:9230": {
            "hostnames": [
                "Hostname|test|c.example.com",
                "Hostname|test|d.example.com",
                "Hostname|test|example.com",
                "Hostname|test|f.example.com",
            ],
            "services": [SystemType.WEB],
        },
    }

    assert len(data["services"]["Dicom"]["IPAddressV4|test|192.0.2.3"]["hostnames"]) == 6
    assert len(data["services"]["Mail"]["IPAddressV4|test|192.0.2.3"]["hostnames"]) == 6
    assert len(data["services"]["Web"]["IPAddressV4|test|192.0.2.3"]["hostnames"]) == 6
    assert len(data["services"]["Other"]["IPAddressV4|test|192.0.2.3"]["hostnames"]) == 6

    assert "IPAddressV6|test|3e4d:64a2:cb49:bd48:a1ba:def3:d15d:9230" not in data["services"]["Dicom"]
    assert "IPAddressV6|test|3e4d:64a2:cb49:bd48:a1ba:def3:d15d:9230" not in data["services"]["Mail"]
    assert "IPAddressV6|test|3e4d:64a2:cb49:bd48:a1ba:def3:d15d:9230" not in data["services"]["Other"]
    assert len(data["services"]["Web"]["IPAddressV6|test|3e4d:64a2:cb49:bd48:a1ba:def3:d15d:9230"]["hostnames"]) == 4

    assert data["open_ports"] == {
        "192.0.2.3": {
            "ports": {22: False, 25: False, 443: False},
            "hostnames": [x.replace("Hostname|test|", "") for x in v4_test_hostnames],
        },
        "3e4d:64a2:cb49:bd48:a1ba:def3:d15d:9230": {
            "ports": {80: False},
            "hostnames": ["c.example.com", "d.example.com", "example.com", "f.example.com"],
        },
    }
    assert data["ipv6"] == {"example.com": {"enabled": True, "systems": ["Dicom", "Mail", "Other", "Web"]}}
    assert data["vulnerabilities"] == {
        "IPAddressV4|test|192.0.2.3": {
            "vulnerabilities": {},
            "summary": {"total_findings": 0, "total_criticals": 0, "terms": [], "recommendations": []},
        },
        "IPAddressV6|test|3e4d:64a2:cb49:bd48:a1ba:def3:d15d:9230": {
            "vulnerabilities": {},
            "summary": {"total_findings": 0, "total_criticals": 0, "terms": [], "recommendations": []},
        },
    }

    assert data["basic_security"]["summary"]["Dicom"] == {
        "rpki": {"number_of_compliant": 1, "total": 1},
        "system_specific": {"number_of_compliant": 0, "total": 0},
        "safe_connections": {"number_of_compliant": 1, "total": 1},
    }
    assert data["basic_security"]["summary"]["Mail"] == {
        "rpki": {"number_of_compliant": 1, "total": 1},
        "system_specific": {
            "number_of_compliant": 1,
            "total": 1,
            "checks": {"SPF": 1, "DKIM": 1, "DMARC": 1},
            "ips": {"IPAddressV4|test|192.0.2.3": []},
        },
        "safe_connections": {"number_of_compliant": 1, "total": 1},
    }
    security_txt_finding_type = KATFindingType(
        id="KAT-NO-SECURITY-TXT",
        description="This hostname does not have a Security.txt file.",
        recommendation="Make sure there is a security.txt available.",
        risk_severity=RiskLevelSeverity.RECOMMENDATION,
    )
    assert data["basic_security"]["summary"]["Web"] == {
        "rpki": {"number_of_compliant": 2, "total": 2},
        "system_specific": {
            "number_of_compliant": 2,
            "total": 2,
            "checks": {
                "CSP Present": 2,
                "Secure CSP Header": 2,
                "Redirects HTTP to HTTPS": 2,
                "Offers HTTPS": 2,
                "Has a Security.txt": 2,
                "No unnecessary ports open": 2,
                "Has a certificate": 2,
                "Certificate is not expired": 2,
                "Certificate is not expiring soon": 2,
            },
            "ips": {
                "IPAddressV4|test|192.0.2.3": [security_txt_finding_type],
                "IPAddressV6|test|3e4d:64a2:cb49:bd48:a1ba:def3:d15d:9230": [security_txt_finding_type],
            },
        },
        "safe_connections": {"number_of_compliant": 2, "total": 2},
    }
    assert data["basic_security"]["summary"]["Other"] == {
        "rpki": {"number_of_compliant": 1, "total": 1},
        "system_specific": {"number_of_compliant": 0, "total": 0},
        "safe_connections": {"number_of_compliant": 1, "total": 1},
    }
