from dataclasses import fields
from functools import reduce
from logging import getLogger

from django.utils.translation import gettext_lazy as _

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

    def post_process_data(self, data):
        systems = {"services": {}}
        services = self.collect_services_by_ip(data)
        open_ports = {}
        ipv6 = {}
        vulnerabilities = {}
        total_criticals = 0
        total_findings = 0
        total_systems = 0
        unique_ips = set()
        unique_hostnames = set()
        terms = []
        rpki = {"rpki_ips": {}}
        safe_connections = {"sc_ips": {}}
        recommendations = []
        total_systems_basic_security = 0

        mail_report_data = self.collect_system_specific_data(data, services, SystemType.MAIL, MailReport.id)
        web_report_data = self.collect_system_specific_data(data, services, SystemType.WEB, WebSystemReport.id)
        dns_report_data = self.collect_system_specific_data(data, services, SystemType.DNS, NameServerSystemReport.id)

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
                            unique_hostnames.update(systems["services"][ip]["hostnames"])
                            systems["services"][ip]["services"] = sorted(
                                set(systems["services"][ip]["services"]) | set(system["services"])
                            )
                    total_systems += report_specific_data["summary"]["total_systems"]

                if report_id == OpenPortsReport.id:
                    for ip, details in report_specific_data.items():
                        open_ports[str(ip)] = details

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
                        total_findings += vulnerabilities_data["summary"]["total_findings"]
                        terms.extend(vulnerabilities_data["summary"]["terms"])
                        recommendations.extend(vulnerabilities_data["summary"]["recommendations"])
                        vulnerabilities[ip] = vulnerabilities_data

                if report_id == RPKIReport.id:
                    rpki["rpki_ips"].update({ip: value for ip, value in report_specific_data["rpki_ips"].items()})

                if report_id == SafeConnectionsReport.id:
                    safe_connections["sc_ips"].update(
                        {ip: value for ip, value in report_specific_data["sc_ips"].items()}
                    )

        for ip, ipv6_data in ipv6.items():
            for system in ipv6_data["systems"]:
                terms.append(str(system))

        # Basic security cleanup
        basic_security = {"rpki": {}, "system_specific": {}, "safe_connections": {}}

        # Safe connections
        for ip, findings in safe_connections["sc_ips"].items():
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

                basic_security["rpki"][service]["rpki_ips"][ip.tokenized.address] = compliance
                basic_security["rpki"][service]["number_of_ips"] += 1
                basic_security["rpki"][service]["number_of_available"] += 1 if compliance["exists"] else 0
                basic_security["rpki"][service]["number_of_valid"] += 1 if compliance["valid"] else 0
                basic_security["rpki"][service]["number_of_compliant"] += (
                    1 if compliance["exists"] and compliance["valid"] else 0
                )

        # System Specific
        basic_security["system_specific"][SystemType.MAIL] = mail_report_data
        basic_security["system_specific"][SystemType.WEB] = web_report_data
        basic_security["system_specific"][SystemType.DNS] = dns_report_data

        # Summary
        basic_security["summary"] = {}

        for service, systems_for_service in services.items():
            # Defaults
            basic_security["summary"][service] = {
                "rpki": {"number_of_compliant": 0, "total": 0},
                "system_specific": {"number_of_compliant": 0, "total": 0},
                "safe_connections": {"number_of_compliant": 0, "total": 0},
            }

            for ip in systems_for_service:
                if ip not in rpki["rpki_ips"]:
                    continue

                basic_security["summary"][service]["rpki"]["number_of_compliant"] += (
                    1 if rpki["rpki_ips"][ip]["exists"] and rpki["rpki_ips"][ip]["valid"] else 0
                )
                basic_security["summary"][service]["rpki"]["total"] += 1

            for ip in systems_for_service:
                if ip not in safe_connections["sc_ips"]:
                    continue

                basic_security["summary"][service]["safe_connections"]["number_of_compliant"] += (
                    1 if not safe_connections["sc_ips"][ip] else 0
                )
                basic_security["summary"][service]["safe_connections"]["total"] += 1

            if service == SystemType.MAIL and mail_report_data:
                check_summary = {}
                for host in mail_report_data:
                    for check in fields(host):
                        if check.name not in check_summary:
                            check_summary[check.name] = 0
                        checkvalue = int(getattr(host, check.name))
                        check_summary[check.name] += checkvalue
                basic_security["summary"][service]["system_specific"] = {
                    "number_of_compliant": sum(
                        m["number_of_hostnames"] == m["number_of_spf"] == m["number_of_dkim"] == m["number_of_dmarc"]
                        for m in mail_report_data
                    ),
                    "total": sum([mail_data["number_of_hostnames"] for mail_data in mail_report_data]),
                    "checks": check_summary,
                }

            if service == SystemType.WEB and web_report_data:
                web_checks = reduce(lambda x, y: x + y, [x["web_checks"] for x in web_report_data])
                check_summary = {}
                for host in web_checks.checks:
                    for check in fields(host):
                        if check.name not in check_summary:
                            check_summary[check.name] = 0
                        checkvalue = int(getattr(host, check.name))
                        check_summary[check.name] += checkvalue
                basic_security["summary"][service]["system_specific"] = {
                    "number_of_compliant": sum(bool(check) for check in web_checks.checks),
                    "total": len(web_checks.checks),
                    "checks": check_summary,
                }

            if service == SystemType.DNS and dns_report_data:
                name_server_checks = reduce(lambda x, y: x + y, [x["name_server_checks"] for x in dns_report_data])
                check_summary = {}
                for host in name_server_checks.checks:
                    for check in fields(host):
                        if check.name not in check_summary:
                            check_summary[check.name] = 0
                        checkvalue = int(getattr(host, check.name))
                        check_summary[check.name] += checkvalue
                basic_security["summary"][service]["system_specific"] = {
                    "number_of_compliant": sum(bool(check) for check in name_server_checks.checks),
                    "total": len(name_server_checks.checks),
                    "checks": check_summary,
                }

        terms = list(set(terms))
        recommendations = list(set(recommendations))

        total_ips = len(unique_ips)
        total_hostnames = len(unique_hostnames)

        summary = {
            # _("General recommendations"): "",
            _("Critical vulnerabilities"): total_criticals,
            _("IPs scanned"): total_ips,
            _("Hostnames scanned"): total_hostnames,
            _("Systems found"): total_systems,
            # _("Sector of organisation"): "",
            # _("Basic security score compared to sector"): "",
            # _("Sector defined"): "",
            # _("Lowest security score in organisation"): "",
            # _("Newly discovered items since last week, october 8th 2023"): "",
            _("Terms in report"): ", ".join(sorted(terms)),
        }

        return {
            "systems": systems,
            "services": services,
            "open_ports": open_ports,
            "ipv6": ipv6,
            "vulnerabilities": vulnerabilities,
            "basic_security": basic_security,
            "summary": summary,
            "total_findings": total_findings,
            "total_systems": total_systems,
            "total_systems_basic_security": total_systems_basic_security,
        }

    def collect_system_specific_data(self, data, services, system_type: SystemType, report_id: str):
        """Given a system, return a list of report data from the right sub-reports based on the related report_id"""

        report_data = []

        for service, systems_for_service in services.items():
            # Search for reports where the input ooi relates to the current service, based on ip or hostname
            for ip, system_for_service in systems_for_service.items():
                # Assumes relevant hostnames have an ip address for now
                if str(ip) in data:
                    if report_id in data[str(ip)] and system_type == service:
                        report_data.append(data[str(ip)][report_id])

                    continue

                for hostname in system_for_service["hostnames"]:
                    if str(hostname) in data:
                        if report_id in data[str(hostname)] and system_type == service:
                            report_data.append(data[str(hostname)][report_id])

                        break

        return report_data

    def collect_services_by_ip(self, data):
        services = {}

        for input_ooi, reports_data in data.items():
            for report_id, report_specific_data in reports_data.items():
                if report_id == SystemReport.id:
                    for ip, system in report_specific_data["services"].items():
                        for service in system["services"]:
                            if service not in services:
                                services[service] = {str(ip): system}
                            else:
                                services[service][str(ip)] = system

        return services
