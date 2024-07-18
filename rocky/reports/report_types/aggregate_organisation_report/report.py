from datetime import datetime
from logging import getLogger
from typing import Any

from django.utils.translation import gettext_lazy as _

from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import OOI
from octopoes.models.exception import ObjectNotFoundException
from octopoes.models.ooi.config import Config
from reports.report_types.definitions import AggregateReport
from reports.report_types.ipv6_report.report import IPv6Report
from reports.report_types.mail_report.report import MailReport
from reports.report_types.name_server_report.report import NameServerSystemReport
from reports.report_types.open_ports_report.report import OpenPortsReport
from reports.report_types.rpki_report.report import RPKIReport
from reports.report_types.safe_connections_report.report import SafeConnectionsReport
from reports.report_types.systems_report.report import SystemReport, SystemType
from reports.report_types.vulnerability_report.report import VulnerabilityReport
from reports.report_types.web_system_report.report import WebSystemReport
from rocky.views.health import flatten_health, get_rocky_health

logger = getLogger(__name__)


class AggregateOrganisationReport(AggregateReport):
    id = "aggregate-organisation-report"
    name = "Aggregate Organisation Report"
    description = "Aggregate Organisation Report"
    reports = {
        "required": [SystemReport],
        "optional": [
            OpenPortsReport,
            VulnerabilityReport,
            IPv6Report,
            RPKIReport,
            MailReport,
            WebSystemReport,
            NameServerSystemReport,
            SafeConnectionsReport,
        ],
    }
    template_path = "aggregate_organisation_report/report.html"

    def post_process_data(self, data: dict[str, Any], valid_time: datetime, organization_code: str) -> dict[str, Any]:
        systems: dict[str, dict[str, Any]] = {"services": {}}
        services = {}
        open_ports = {}
        ipv6 = {}
        vulnerabilities = {}
        total_criticals = 0
        total_systems = 0
        unique_ips = set()
        unique_hostnames = set()
        terms = []
        rpki_ips = {}
        safe_connections_ips = {}
        recommendations = []
        total_systems_basic_security = 0

        for input_ooi, reports_data in data.items():
            for report_id, report_specific_data in reports_data.items():
                # data in report, specifically we use systems to couple reports

                if report_id == SystemReport.id:
                    for ip, system in report_specific_data["services"].items():
                        unique_ips.add(ip)

                        if ip not in systems["services"]:
                            systems["services"][ip] = system
                        else:
                            # makes sure that there are no duplicates in the list
                            systems["services"][ip]["hostnames"] = sorted(
                                set(systems["services"][ip]["hostnames"]) | set(system["hostnames"])
                            )

                            systems["services"][ip]["services"] = sorted(
                                set(systems["services"][ip]["services"]) | set(system["services"])
                            )

                        for service in system["services"]:
                            if service not in services:
                                services[service] = {ip: systems["services"][ip]}
                            else:
                                services[service][ip] = systems["services"][ip]
                        unique_hostnames.update(systems["services"][ip]["hostnames"])
                    total_systems += report_specific_data["summary"]["total_systems"]

                if report_id == OpenPortsReport.id:
                    for ip, details in report_specific_data.items():
                        open_ports[ip] = details

                if report_id == IPv6Report.id:
                    for hostname, info in report_specific_data.items():
                        ipv6[hostname] = {"enabled": info["enabled"], "systems": []}

                        for ip, system in systems["services"].items():
                            if hostname in [x.tokenized.name for x in system["hostnames"]]:
                                ipv6[hostname]["systems"] = sorted(
                                    set(ipv6[hostname]["systems"]).union(set(system["services"]))
                                )

                if report_id == VulnerabilityReport.id:
                    for ip, vulnerabilities_data in report_specific_data.items():
                        terms.extend(vulnerabilities_data["summary"]["terms"])
                        recommendations.extend(vulnerabilities_data["summary"]["recommendations"])
                        vulnerabilities_data["title"] = ip.split("|")[2]
                        vulnerabilities[ip] = vulnerabilities_data

                if report_id == RPKIReport.id:
                    rpki_ips.update({ip: value for ip, value in report_specific_data["rpki_ips"].items()})

                if report_id == SafeConnectionsReport.id:
                    safe_connections_ips.update({ip: value for ip, value in report_specific_data["sc_ips"].items()})

        mail_report_data = self.collect_system_specific_data(data, services, SystemType.MAIL, MailReport.id)
        web_report_data = self.collect_system_specific_data(data, services, SystemType.WEB, WebSystemReport.id)
        dns_report_data = self.collect_system_specific_data(data, services, SystemType.DNS, NameServerSystemReport.id)

        for ip, ipv6_data in ipv6.items():
            for system in ipv6_data["systems"]:
                terms.append(str(system))

        # Basic security cleanup
        basic_security: dict[str, Any] = {"rpki": {}, "system_specific": {}, "safe_connections": {}}

        # Safe connections
        for ip, findings in safe_connections_ips.items():
            ip_services = systems["services"][str(ip)]["services"]

            for service in ip_services:
                if service not in basic_security["safe_connections"]:  # Set initial value
                    basic_security["safe_connections"][service] = {
                        "sc_ips": {},
                        "number_of_available": 0,
                        "number_of_ips": 0,
                    }

                if ip in basic_security["safe_connections"][service]["sc_ips"]:
                    continue  # We already processed data from this ip for this service

                basic_security["safe_connections"][service]["sc_ips"][ip.tokenized.address] = findings
                basic_security["safe_connections"][service]["number_of_ips"] += 1
                basic_security["safe_connections"][service]["number_of_available"] += 1 if not findings else 0

                # Collect recommendations from findings
                recommendations.extend({finding_type.recommendation for finding_type in findings})

        # RPKI
        for ip, compliance in rpki_ips.items():
            ip_services = systems["services"][str(ip)]["services"]

            for service in services:
                service = str(service)
                if service not in basic_security["rpki"]:  # Set initial value
                    basic_security["rpki"][service] = {
                        "rpki_ips": {},
                        "number_of_available": 0,
                        "number_of_valid": 0,
                        "number_of_ips": 0,
                        "number_of_compliant": 0,
                    }

                if ip in basic_security["rpki"][service]["rpki_ips"]:
                    continue  # We already processed data from this ip for this service

                basic_security["rpki"][service]["rpki_ips"][ip.tokenized.address] = compliance
                basic_security["rpki"][service]["number_of_ips"] += 1
                basic_security["rpki"][service]["number_of_available"] += 1 if compliance["exists"] else 0
                basic_security["rpki"][service]["number_of_valid"] += 1 if compliance["valid"] else 0
                basic_security["rpki"][service]["number_of_compliant"] += (
                    1 if compliance["exists"] and compliance["valid"] else 0
                )

        # System Specific
        basic_security["system_specific"][SystemType.MAIL] = [
            report for ip in mail_report_data for report in mail_report_data[ip]
        ]
        basic_security["system_specific"][SystemType.WEB] = [
            report for ip in web_report_data for report in web_report_data[ip]
        ]
        basic_security["system_specific"][SystemType.DNS] = [
            report for ip in dns_report_data for report in dns_report_data[ip]
        ]

        # Summary
        basic_security["summary"] = {}

        for service, systems_for_service in services.items():
            # Defaults
            basic_security["summary"][service] = {
                "rpki": {"number_of_compliant": 0, "total": 0},
                "system_specific": {"number_of_compliant": 0, "total": 0, "checks": {}, "ips": {}},
                "safe_connections": {"number_of_compliant": 0, "total": 0},
            }

            for ip in systems_for_service:
                if ip not in rpki_ips:
                    continue

                basic_security["summary"][service]["rpki"]["number_of_compliant"] += (
                    1 if rpki_ips[ip]["exists"] and rpki_ips[ip]["valid"] else 0
                )
                basic_security["summary"][service]["rpki"]["total"] += 1

            for ip in systems_for_service:
                if ip not in safe_connections_ips:
                    continue

                basic_security["summary"][service]["safe_connections"]["number_of_compliant"] += (
                    1 if not safe_connections_ips[ip] else 0
                )
                basic_security["summary"][service]["safe_connections"]["total"] += 1

            if service == SystemType.MAIL and mail_report_data:

                def spf_compliant(result):
                    return result["number_of_hostnames"] == result["number_of_spf"]

                def dkim_compliant(result):
                    return result["number_of_hostnames"] == result["number_of_dkim"]

                def dmarc_compliant(result):
                    return result["number_of_hostnames"] == result["number_of_dmarc"]

                def is_mail_compliant(result):
                    return all(check(result) for check in [spf_compliant, dkim_compliant, dmarc_compliant])

                basic_security["summary"][service]["system_specific"] = {
                    "number_of_compliant": sum(
                        all(is_mail_compliant(m) for m in mail_report_data[ip]) for ip in mail_report_data
                    ),
                    "total": len(mail_report_data),
                    "checks": {
                        "SPF": sum(all(spf_compliant(m) for m in mail_report_data[ip]) for ip in mail_report_data),
                        "DKIM": sum(all(dkim_compliant(m) for m in mail_report_data[ip]) for ip in mail_report_data),
                        "DMARC": sum(all(dmarc_compliant(m) for m in mail_report_data[ip]) for ip in mail_report_data),
                    },
                    "ips": {
                        ip: sorted(
                            {  # Flattening the finding_types field of the mail report output
                                finding_type
                                for mail_report in mail_report_data[ip]
                                for finding_type in mail_report["finding_types"]
                            },
                            reverse=True,
                            key=lambda x: x.risk_severity,
                        )
                        for ip in mail_report_data
                    },
                }

            if service == SystemType.WEB and web_report_data:
                basic_security["summary"][service]["system_specific"] = {
                    "number_of_compliant": sum(
                        all(result["web_checks"] for result in web_report_data[ip]) for ip in web_report_data
                    ),
                    "total": len(web_report_data),
                    "checks": {
                        "CSP Present": sum(
                            all(w["web_checks"].has_csp for w in web_report_data[ip]) for ip in web_report_data
                        ),
                        "Secure CSP Header": sum(
                            all(w["web_checks"].has_no_csp_vulnerabilities for w in web_report_data[ip])
                            for ip in web_report_data
                        ),
                        "Redirects HTTP to HTTPS": sum(
                            all(w["web_checks"].redirects_http_https for w in web_report_data[ip])
                            for ip in web_report_data
                        ),
                        "Offers HTTPS": sum(
                            all(w["web_checks"].offers_https for w in web_report_data[ip]) for ip in web_report_data
                        ),
                        "Has a Security.txt": sum(
                            all(w["web_checks"].has_security_txt for w in web_report_data[ip]) for ip in web_report_data
                        ),
                        "No unnecessary ports open": sum(
                            all(w["web_checks"].no_uncommon_ports for w in web_report_data[ip])
                            for ip in web_report_data
                        ),
                        "Has a certificate": sum(
                            all(w["web_checks"].has_certificates for w in web_report_data[ip]) for ip in web_report_data
                        ),
                        "Certificate is not expired": sum(
                            all(w["web_checks"].certificates_not_expired for w in web_report_data[ip])
                            for ip in web_report_data
                        ),
                        "Certificate is not expiring soon": sum(
                            all(w["web_checks"].certificates_not_expiring_soon for w in web_report_data[ip])
                            for ip in web_report_data
                        ),
                    },
                    "ips": {
                        ip: sorted(
                            {  # Flattening the finding_types field of the web report output
                                finding_type
                                for web_report in web_report_data[ip]
                                for finding_type in web_report["finding_types"]
                            },
                            reverse=True,
                            key=lambda x: x.risk_severity,
                        )
                        for ip in web_report_data
                    },
                }

            if service == SystemType.DNS and dns_report_data:
                basic_security["summary"][service]["system_specific"] = {
                    "number_of_compliant": sum(
                        all(result["name_server_checks"] for result in dns_report_data[ip]) for ip in dns_report_data
                    ),
                    "total": len(dns_report_data),
                    "checks": {
                        "DNSSEC Present": sum(
                            all(n["name_server_checks"].has_dnssec for n in dns_report_data[ip])
                            for ip in dns_report_data
                        ),
                        "Valid DNSSEC": sum(
                            all(n["name_server_checks"].has_valid_dnssec for n in dns_report_data[ip])
                            for ip in dns_report_data
                        ),
                        "No unnecessary ports open": sum(
                            all(n["name_server_checks"].no_uncommon_ports for n in dns_report_data[ip])
                            for ip in dns_report_data
                        ),
                    },
                    "ips": {
                        ip: sorted(
                            {  # Flattening the finding_types field of the dns report output
                                finding_type
                                for dns_report in dns_report_data[ip]
                                for finding_type in dns_report["finding_types"]
                            },
                            reverse=True,
                            key=lambda x: x.risk_severity,
                        )
                        for ip in dns_report_data
                    },
                }

            # Collect recommendations from findings
            if (
                service == SystemType.MAIL
                and mail_report_data
                or service == SystemType.WEB
                and web_report_data
                or service == SystemType.DNS
                and dns_report_data
            ):
                recommendations.extend(
                    {
                        finding_type.recommendation
                        for ip, finding in basic_security["summary"][service]["system_specific"]["ips"].items()
                        for finding_type in finding
                    }
                )

        terms = list(set(terms))

        recommendation_counts = {}

        for recommendation in recommendations:
            if recommendation not in recommendation_counts:
                recommendation_counts[recommendation] = 0

            recommendation_counts[recommendation] += 1

        recommendations = list(set(filter(None, recommendations)))
        total_ips = len(unique_ips)
        total_hostnames = len(unique_hostnames)
        total_criticals = sum(vulnerability["summary"]["total_criticals"] for vulnerability in vulnerabilities.values())

        summary = {
            # _("General recommendations"): "",
            str(_("Critical vulnerabilities")): total_criticals,
            str(_("IPs scanned")): total_ips,
            str(_("Hostnames scanned")): total_hostnames,
            # _("Systems found"): total_systems,
            # _("Sector of organisation"): "",
            # _("Basic security score compared to sector"): "",
            # _("Sector defined"): "",
            # _("Lowest security score in organisation"): "",
            # _("Newly discovered items since last week, october 8th 2023"): "",
            str(_("Terms in report")): ", ".join(sorted(terms)),
        }

        all_findings = set()
        for ip, ip_data in vulnerabilities.items():
            for vulnerability, vulnerability_data in ip_data.get("vulnerabilities", {}).items():
                for finding_key in vulnerability_data.get("findings", {}):
                    all_findings.add(finding_key)

        config_oois = self.octopoes_api_connector.list_objects(types={Config}, valid_time=valid_time).items

        flattened_health = flatten_health(get_rocky_health(organization_code, self.octopoes_api_connector))

        return {
            "systems": systems,
            "services": services,
            "recommendations": recommendations,
            "recommendation_counts": recommendation_counts,
            "open_ports": open_ports,
            "ipv6": ipv6,
            "vulnerabilities": vulnerabilities,
            "basic_security": basic_security,
            "summary": summary,
            "total_findings": len(all_findings),
            "total_systems": total_ips,
            "total_hostnames": total_hostnames,
            "total_systems_basic_security": total_systems_basic_security,
            "health": [health.dict() for health in flattened_health],
            "config_oois": config_oois,
        }

    def collect_system_specific_data(self, data, services, system_type: str, report_id: str) -> dict[str, Any]:
        """Given a system, return a list of report data from the right sub-reports based on the related report_id"""

        report_data: dict[str, Any] = {}

        for service, systems_for_service in services.items():
            # Search for reports where the input ooi relates to the current service, based on ip or hostname
            for ip, system_for_service in systems_for_service.items():
                # Assumes relevant hostnames have an ip address for now
                if ip not in report_data:
                    report_data[ip] = []

                if ip in data and report_id in data[str(ip)] and system_type == service:
                    report_data[ip].append(data[str(ip)][report_id])

                for hostname in system_for_service["hostnames"]:
                    if str(hostname) in data and report_id in data[str(hostname)] and system_type == service:
                        report_data[ip].append(data[str(hostname)][report_id])

        report_data = {key: value for key, value in report_data.items() if value}

        return report_data


def aggregate_reports(
    connector: OctopoesAPIConnector,
    input_ooi_references: list[OOI],
    selected_report_types: list[str],
    valid_time: datetime,
    organization_code: str,
) -> tuple[AggregateOrganisationReport, dict[str, Any], dict[str, Any], list[str]]:
    by_type: dict[str, list[str]] = {}

    for ooi in input_ooi_references:
        if ooi.get_object_type() not in by_type:
            by_type[ooi.get_object_type()] = []

        by_type[ooi.get_object_type()].append(str(ooi.reference))

    all_types = [
        t
        for t in AggregateOrganisationReport.reports["required"] + AggregateOrganisationReport.reports["optional"]
        if t.id in selected_report_types
    ]
    report_data: dict[str, Any] = {}
    errors = []

    for report_type in all_types:
        oois = {x for ooi_type in report_type.input_ooi_types for x in by_type.get(ooi_type.get_object_type(), [])}

        try:
            results = report_type(connector).collect_data(oois, valid_time)
        except ObjectNotFoundException:
            logger.error("Object not found")
            errors.append(report_type.id)
            continue

        for ooi_str, data in results.items():
            if ooi_str not in report_data:
                report_data[ooi_str] = {}

            report_data[ooi_str][report_type.id] = data

    aggregate_report = AggregateOrganisationReport(connector)
    post_processed_data = aggregate_report.post_process_data(report_data, valid_time, organization_code)

    return aggregate_report, post_processed_data, report_data, errors
