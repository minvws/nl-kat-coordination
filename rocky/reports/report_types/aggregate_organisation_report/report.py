from logging import getLogger

from reports.report_types.definitions import AggregateReport
from reports.report_types.ipv6_report.report import IPv6Report
from reports.report_types.open_ports_report.report import OpenPortsReport
from reports.report_types.systems_report.report import SystemsReport
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
    reports = {"required": [SystemsReport, OpenPortsReport, IPv6Report], "optional": [VulnerabilityReport]}
    template_path = "aggregate_organisation_report/report.html"

    def post_process_data(self, data):
        systems = []
        open_ports = {}
        ipv6 = {}
        vulnerabilities = {}
        # input oois

        for input_ooi, report_data in data.items():
            # reports
            for report, data in report_data.items():
                # data in report, specifically we use system to couple reports
                if report == "System Report":
                    for system in data["data"]["systems"]:
                        add_or_combine_systems(systems, system)

                if report == "Open Ports Report":
                    open_ports = data["data"]["ports"]

                if report == "IPv6 Report":
                    for hostname, enabled in data["data"]["results"].items():
                        ipv6[hostname] = enabled
                if report == "Vulnerability Report":
                    vulnerabilities.update(data["data"])

        return {"systems": systems, "open_ports": open_ports, "ipv6": ipv6, "vulnerabilities": vulnerabilities}
