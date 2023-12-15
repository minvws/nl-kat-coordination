from logging import getLogger

from django.utils.translation import gettext_lazy as _

from reports.report_types.definitions import AggregateReport
from reports.report_types.ipv6_report.report import IPv6Report
from reports.report_types.mail_report.report import MailReport
from reports.report_types.open_ports_report.report import OpenPortsReport
from reports.report_types.rpki_report.report import RPKIReport
from reports.report_types.systems_report.report import SystemReport
from reports.report_types.vulnerability_report.report import VulnerabilityReport

logger = getLogger(__name__)


class AggregateOrganisationReport(AggregateReport):
    id = "aggregate-organisation-report"
    name = "Aggregate Organisation Report"
    description = "Aggregate Organisation Report"
    reports = {"required": [SystemReport], "optional": [OpenPortsReport, VulnerabilityReport, IPv6Report, RPKIReport, MailReport]}
    template_path = "aggregate_organisation_report/report.html"

    def post_process_data(self, data):
        systems = {"services": {}}
        services = {}
        open_ports = {}
        ipv6 = {}
        vulnerabilities = {}
        total_criticals = 0
        total_findings = 0
        total_ips = 0
        total_hostnames = 0
        terms = []
        rpki = {"rpki_ips": {}}
        recommendations = []
        mail_report_data = []
        total_systems_basic_security = 0

        for input_ooi, reports_data in data.items():
            for report_id, report_specific_data in reports_data.items():
                # data in report, specifically we use systems to couple reports

                if report_id == SystemReport.id:
                    for ip, system in report_specific_data["services"].items():
                        for service in system["services"]:
                            if service not in services:
                                services[service] = {ip: system}
                            else:
                                services[service][ip] = system

                        if ip not in systems["services"]:
                            systems["services"][ip] = system
                        else:
                            # makes sure that there are no duplicates in the list
                            systems["services"][ip]["hostnames"] = list(
                                set(systems["services"][ip]["hostnames"]) | set(system["hostnames"])
                            )
                            systems["services"][ip]["services"] = list(
                                set(systems["services"][ip]["services"]) | set(system["services"])
                            )
                    total_ips += report_specific_data["summary"]["total_systems"]
                    total_hostnames += report_specific_data["summary"]["total_domains"]

                if report_id == OpenPortsReport.id:
                    for ip, details in report_specific_data.items():
                        open_ports[ip] = details

                if report_id == IPv6Report.id:
                    for hostname, info in report_specific_data.items():
                        ipv6[hostname] = {"enabled": info["enabled"], "systems": []}

                        for ip, system in systems["services"].items():
                            if hostname in system["hostnames"]:
                                ipv6[hostname]["systems"] = list(
                                    set(ipv6[hostname]["systems"]).union(set(system["services"]))
                                )

                if report_id == VulnerabilityReport.id:
                    total_criticals += report_specific_data["summary"]["total_criticals"]
                    total_findings += report_specific_data["summary"]["total_findings"]
                    terms.extend(report_specific_data["summary"]["terms"])
                    recommendations.extend(report_specific_data["summary"]["recommendations"])
                    vulnerabilities[input_ooi] = report_specific_data

                if report_id == RPKIReport.id:
                    rpki["rpki_ips"].update(report_specific_data["rpki_ips"])

                if report_id == MailReport.id:
                    mail_report_data.append(report_specific_data)

        for ip, ipv6_data in ipv6.items():
            for system in ipv6_data["systems"]:
                terms.append(str(system))

        # Basic security cleanup
        basic_security = {"rpki": {}}

        # RPKI
        for ip, compliance in rpki["rpki_ips"].items():
            ip_services = systems["services"][str(ip)]["services"]

            for service in ip_services:
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

                basic_security["rpki"][service]["rpki_ips"][ip] = compliance
                basic_security["rpki"][service]["number_of_ips"] += 1
                basic_security["rpki"][service]["number_of_available"] += 1 if compliance["exists"] else 0
                basic_security["rpki"][service]["number_of_valid"] += 1 if compliance["valid"] else 0
                basic_security["rpki"][service]["number_of_compliant"] += (
                    1 if compliance["exists"] and compliance["valid"] else 0
                )

        basic_security["summary"] = {}

        for service, systems in services.items():
            # Defaults
            basic_security["summary"][service] = {
                "rpki": {"number_of_compliant": 0, "total": 0},
                "system_specific": {"number_of_compliant": 0, "total": 0},
                "safe_connections": {"number_of_compliant": 0, "total": 0},
            }

            for ip, system in systems.items():
                if ip not in rpki["rpki_ips"]:
                    continue

                basic_security["summary"][service]["rpki"]["number_of_compliant"] += (
                    1 if rpki["rpki_ips"][ip]["exists"] and rpki["rpki_ips"][ip]["valid"] else 0
                )
                basic_security["summary"][service]["rpki"]["total"] += 1

            if service == "Mail":
                basic_security["summary"][service]["system_specific"] = {
                    "number_of_compliant": sum(
                        m["number_of_hostnames"] == m["number_of_spf"] == m["number_of_dkim"] == m["number_of_dmarc"]
                        for m in mail_report_data
                    ),
                    "total": sum([mail_data["number_of_hostnames"] for mail_data in mail_report_data]),
                }

        terms = list(set(terms))
        recommendations = list(set(recommendations))

        summary = {
            _("General recommendations"): "",
            _("Critical vulnerabilities"): total_criticals,
            _("IPs scanned"): total_ips,
            _("Domains scanned"): total_hostnames,
            _("Sector of organisation"): "",
            _("Basic security score compared to sector"): "",
            _("Sector defined"): "",
            _("Lowest security score in organisation"): "",
            _("Newly discovered items since last week, october 8th 2023"): "",
            _("Terms in report"): ", ".join(terms),
        }

        return {
            "systems": systems,
            "services": services,
            "open_ports": open_ports,
            "ipv6": ipv6,
            "vulnerabilities": vulnerabilities,
            "basic_security": basic_security,
            "summary": summary,
            "recommendations": recommendations,
            "total_findings": total_findings,
            "total_systems": total_ips,
            "total_systems_basic_security": total_systems_basic_security,
        }
