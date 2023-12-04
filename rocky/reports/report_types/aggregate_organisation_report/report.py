from logging import getLogger

from django.utils.translation import gettext_lazy as _

from reports.report_types.definitions import AggregateReport
from reports.report_types.ipv6_report.report import IPv6Report
from reports.report_types.open_ports_report.report import OpenPortsReport
from reports.report_types.systems_report.report import SystemReport
from reports.report_types.vulnerability_report.report import VulnerabilityReport

logger = getLogger(__name__)


class AggregateOrganisationReport(AggregateReport):
    id = "aggregate-organisation-report"
    name = "Aggregate Organisation Report"
    description = "Aggregate Organisation Report"
    reports = {"required": [SystemReport, OpenPortsReport, IPv6Report], "optional": [VulnerabilityReport]}
    template_path = "aggregate_organisation_report/report.html"

    def get_summary(self):
        summary = {
            _("General recommendations"): 3,
            _("Critical vulnerabilities"): 1,
            _("Assets (IP/domains) scanned"): "x",
            _("Indemnification"): "xxxxx",
            _("Sector of organisation"): "This is a sector definition to make it clear for the rest of the report "
            "what all the comparisons between percentages mean",
            _("Basic security score compared to sector"): "Score 80%, Sector: 77,5%",
            _("Sector defined"): "All healthcare organisations that use KAT for example.",
            _("Lowest security score in organisation"): "System specific",
            _("Newly discovered items since last week, october 8th 2023"): "1 systeem",
            _("Terms in report"): ["DNS", "SPF"],
        }
        return summary

    def get_total_vulnerabilities(self, vulnerabilities) -> int:
        total_vulnerabilities = 0
        for finding, finding_details in vulnerabilities.items():
            total_vulnerabilities += finding_details["occurrences"]
        return total_vulnerabilities

    def post_process_data(self, data):
        systems = {"services": {}}
        open_ports = {}
        ipv6 = {}
        vulnerabilities = {}

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
                    data["data"]["total_findings"] = self.get_total_vulnerabilities(data["data"])
                    vulnerabilities[input_ooi] = data["data"]

        return {
            "summary": self.get_summary(),
            "systems": systems,
            "open_ports": open_ports,
            "ipv6": ipv6,
            "vulnerabilities": vulnerabilities,
        }
