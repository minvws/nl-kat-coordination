from logging import getLogger
from typing import Any, Dict

from django.utils.translation import gettext_lazy as _

from reports.report_types.definitions import AggregateReport
from reports.report_types.ipv6_report.report import IPv6Report
from reports.report_types.open_ports_report.report import OpenPortsReport
from reports.report_types.systems_report.report import SystemReport
from reports.report_types.vulnerability_report.report import VulnerabilityReport

logger = getLogger(__name__)


def add_or_combine_systems(systems, new_system):
    for system in systems:
        if set(system.oois) == set(new_system.oois):
            system.system_types.extend(x for x in new_system.system_types if x not in system.system_types)
            return
    systems.append(new_system)


class AggregateOrganisationReport(AggregateReport):
    id = "aggregate-organisation-report"
    name = "Aggregate Organisation Report"
    description = "Aggregate Organisation Report"
    reports = {"required": [SystemReport, OpenPortsReport, IPv6Report], "optional": [VulnerabilityReport]}
    template_path = "aggregate_organisation_report/report.html"

    def get_summary(self, data: Dict[str, Any]):
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

    def post_process_data(self, data):
        systems = {"services": {}}
        open_ports = {}
        ipv6 = {}
        vulnerabilities = {}
        summary = {}

        # input oois

        for input_ooi, report_data in data.items():
            # reports
            for report, data in report_data.items():
                # data in report, specifically we use system to couple reports
                if report == "System Report":
                    systems["services"].update(data["data"]["services"])

                if report == "Open Ports Report":
                    open_ports[data["data"]["ip"]] = {
                        "ports": data["data"]["ports"],
                        "hostnames": data["data"]["hostnames"],
                    }

                if report == "IPv6 Report":
                    for hostname, enabled in data["data"]["results"].items():
                        ipv6[hostname] = enabled
                if report == "Vulnerability Report":
                    vulnerabilities.update(data["data"])

        return {
            "summary": summary,
            "systems": systems,
            "open_ports": open_ports,
            "ipv6": ipv6,
            "vulnerabilities": vulnerabilities,
        }
