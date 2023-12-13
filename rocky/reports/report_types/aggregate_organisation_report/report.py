from logging import getLogger

from django.utils.translation import gettext_lazy as _

from reports.report_types.definitions import AggregateReport
from reports.report_types.ipv6_report.report import IPv6Report
from reports.report_types.open_ports_report.report import OpenPortsReport
from reports.report_types.rpki_report.report import RPKIReport
from reports.report_types.systems_report.report import SystemReport
from reports.report_types.vulnerability_report.report import VulnerabilityReport

logger = getLogger(__name__)


class AggregateOrganisationReport(AggregateReport):
    id = "aggregate-organisation-report"
    name = "Aggregate Organisation Report"
    description = "Aggregate Organisation Report"
    reports = {"required": [SystemReport], "optional": [OpenPortsReport, VulnerabilityReport, IPv6Report, RPKIReport]}
    template_path = "aggregate_organisation_report/report.html"
    summary = {
        _("General recommendations"): "",
        _("Critical vulnerabilities"): 0,
        _("Assets (IP/domains) scanned"): 0,
        _("Sector of organisation"): "",
        _("Basic security score compared to sector"): "",
        _("Sector defined"): "",
        _("Lowest security score in organisation"): "",
        _("Newly discovered items since last week, october 8th 2023"): "",
        _("Terms in report"): "",
    }

    def post_process_data(self, data):
        systems = {"services": {}}
        open_ports = {}
        ipv6 = {}
        vulnerabilities = {}
        total_criticals = 0
        total_findings = 0
        total_ips = 0
        total_hostnames = 0
        terms = []
        rpki = {"rpki_ips": {}}
        system_specific = {}
        recommendations = []

        # input oois
        for input_ooi, report_data in data.items():
            # reports
            for report, data in report_data.items():
                # data in report, specifically we use system to couple reports
                if report == "System Report":
                    for ip, system in data["data"]["services"].items():
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
                    total_ips += data["data"]["summary"]["total_systems"]
                    total_hostnames += data["data"]["summary"]["total_domains"]

                if report == "Open Ports Report":
                    open_ports[data["data"]["ip"]] = {
                        "ports": data["data"]["ports"],
                        "hostnames": data["data"]["hostnames"],
                    }

                if report == "IPv6 Report":
                    for hostname, info in data["data"].items():
                        ipv6[hostname] = {"enabled": info["enabled"], "systems": []}

                        for ip, system in systems["services"].items():
                            if hostname in system["hostnames"]:
                                ipv6[hostname]["systems"] = list(
                                    set(ipv6[hostname]["systems"]).union(set(system["services"]))
                                )

                if report == "Vulnerability Report":
                    total_criticals += data["data"]["summary"]["total_criticals"]
                    total_findings += data["data"]["summary"]["total_findings"]
                    terms.extend(data["data"]["summary"]["terms"])
                    recommendations.extend(data["data"]["summary"]["recommendations"])
                    vulnerabilities[input_ooi] = data["data"]

                if report == "RPKI Report":
                    logger.error(data["data"])
                    rpki["rpki_ips"].update(data["data"]["rpki_ips"])

        for ip, data in ipv6.items():
            for system in data["systems"]:
                terms.append(str(system))

        # Basic security cleanup
        # RPKI
        for ip, compliance in rpki["rpki_ips"].items():
            services = systems["services"][str(ip)]["services"]
            for service in services:
                if service not in system_specific:
                    system_specific[service] = {
                        "rpki": {
                            "rpki_ips": {},
                            "number_of_available": 0,
                            "number_of_valid": 0,
                            "number_of_ips": 0,
                            "number_of_compliant": 0,
                        }
                    }
                if ip not in system_specific[service]["rpki"]["rpki_ips"]:
                    system_specific[service]["rpki"]["rpki_ips"][ip] = compliance
                    system_specific[service]["rpki"]["number_of_ips"] += 1
                    system_specific[service]["rpki"]["number_of_available"] += 1 if compliance["exists"] else 0
                    system_specific[service]["rpki"]["number_of_valid"] += 1 if compliance["valid"] else 0
                    system_specific[service]["rpki"]["number_of_compliant"] += (
                        1 if compliance["exists"] and compliance["valid"] else 0
                    )

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
            "open_ports": open_ports,
            "ipv6": ipv6,
            "vulnerabilities": vulnerabilities,
            "system_specific": system_specific,
            "summary": summary,
            "recommendations": recommendations,
            "total_findings": total_findings,
            "total_systems": total_ips,
        }
