from datetime import datetime
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

    def get_summary(self, valid_time: datetime, input_ooi: str):
        vulnerability_summary = VulnerabilityReport.get_summary(input_ooi, self.octopoes_api_connector, valid_time)
        return vulnerability_summary

    def get_total_vulnerabilities(self, vulnerabilities) -> int:
        total_vulnerabilities = 0
        for finding, finding_details in vulnerabilities.items():
            total_vulnerabilities += finding_details["occurrences"]
        return total_vulnerabilities

    def post_process_data(self, valid_time, data):
        systems = {"services": {}}
        open_ports = {}
        ipv6 = {}
        vulnerabilities = {}
        self.summary["Critical vulnerabilities"] = 0
        self.summary["Assets (IP/domains) scanned"] = len(data.values())

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
                    open_ports.update(data["data"])

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

            self.summary["Critical vulnerabilities"] += self.get_summary(
                valid_time,
                input_ooi,
            )["critical_vulnerabilities"]

        return {
            "summary": self.summary,
            "systems": systems,
            "open_ports": open_ports,
            "ipv6": ipv6,
            "vulnerabilities": vulnerabilities,
        }
