from logging import getLogger
from typing import Any, Dict, List

from django.utils.translation import gettext_lazy as _

from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import Reference
from octopoes.models.ooi.reports import ReportData
from reports.report_types.definitions import MultiReport

logger = getLogger(__name__)


class MultiOrganizationReport(MultiReport):
    id = "multi-organization-report"
    name = _("Multi Organization Report")
    description = _("Multi Organization Report")
    plugins = {"required": [], "optional": []}
    input_ooi_types = {ReportData}
    template_path = "multi_organization_report/report.html"

    def post_process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        The data is of the form:
           {
               "ReportData|org_code": ReportData.dict(),
               "ReportData|org_code_2": ReportData.dict(),
           }
        """

        tags = {}
        total_critical_vulnerabilities = 0
        basic_securities = []
        total_findings = 0
        total_systems = 0
        total_hostnames = 0
        service_counts = {}
        asset_vulnerabilities = []
        open_ports = {"total": 0, "ports": {}}
        services = {}
        basic_security_summary = {}
        safe_connections_summary = {"number_of_available": 0, "number_of_ips": 0}
        system_specific = {}

        for report_data in data.values():
            basic_security = {"compliant": 0, "total": 0}

            for tag in report_data["organization_tags"]:
                if tag not in tags:
                    tags[tag] = []

                tags[tag].append(report_data["organization_code"])

            aggregate_data = report_data["data"]["post_processed_data"]
            total_critical_vulnerabilities += aggregate_data["summary"]["Critical vulnerabilities"]
            total_findings += aggregate_data["total_findings"]
            total_systems += aggregate_data["total_systems"]
            total_hostnames += aggregate_data["total_hostnames"]

            for compliance in report_data["data"]["post_processed_data"]["basic_security"]["summary"].values():
                for counts in compliance.values():
                    basic_security["total"] += counts["total"]
                    basic_security["compliant"] += counts["number_of_compliant"]

            basic_securities.append(basic_security)

            for service, systems in aggregate_data["services"].items():
                if service not in service_counts:
                    service_counts[service] = 0

                service_counts[service] += len(systems)

            for system, vulnerabilities in aggregate_data["vulnerabilities"].items():
                row = {
                    "asset": system,
                    "vulnerabilities": vulnerabilities["summary"]["terms"],
                    "organisation": report_data["organization_code"],
                }
                asset_vulnerabilities.append(row)

            for system, ports in aggregate_data["open_ports"].items():
                open_ports["total"] += 1

                for port in ports["ports"]:
                    if port not in open_ports["ports"]:
                        open_ports["ports"][port] = {"open": 0, "services": set()}

                    open_ports["ports"][port]["open"] += 1
                    open_ports["ports"][port]["services"] |= set(ports["services"][port])

            for service, systems in aggregate_data["services"].items():
                if service not in services:
                    services[service] = []

                services[service].extend(systems)

            for service, row in aggregate_data["basic_security"]["summary"].items():
                if service not in basic_security_summary:
                    basic_security_summary[service] = {
                        "rpki": {"number_of_compliant": 0, "total": 0},
                        "system_specific": {"number_of_compliant": 0, "total": 0},
                        "safe_connections": {"number_of_compliant": 0, "total": 0},
                    }

                for column in ["rpki", "system_specific", "safe_connections"]:
                    basic_security_summary[service][column]["number_of_compliant"] += row[column]["number_of_compliant"]
                    basic_security_summary[service][column]["total"] += row[column]["total"]

            for service, safe_connections in aggregate_data["basic_security"]["safe_connections"].items():
                safe_connections_summary["number_of_available"] += safe_connections["number_of_available"]
                safe_connections_summary["number_of_ips"] += safe_connections["number_of_ips"]

            for service, summary in aggregate_data["basic_security"]["summary"].items():
                if service not in system_specific:
                    system_specific[service] = {"checks": {}}

                for title, count in summary["system_specific"]["checks"].items():
                    if title not in system_specific[service]["checks"]:
                        system_specific[service]["checks"][title] = 0

                    system_specific[service]["checks"][title] += count

        # TODO:
        #  - Sectornaam
        #  - “Sector X”
        #  - Benchmark comparison X ?
        #  - Best scoring security checks
        #  - Lowest organisations in report
        #  - Lowest organisations in report per tag
        #  - Most common vulnerabilities
        #  - Disclaimer
        #  - Recommendations table
        #  - total_ip_ranges
        #  - hrefs
        #  - safe connections score vs. sector
        #  -

        return {
            "multi_data": data,
            "organizations": [value["organization_code"] for key, value in data.items()],
            "tags": tags,
            # Average score over organizations
            "basic_security_score": round(
                sum(x["compliant"] / x["total"] for x in basic_securities) / len(basic_securities) * 100
            ),
            "median_vulnerabilities": 60,  # TODO
            "total_critical_vulnerabilities": total_critical_vulnerabilities,
            "total_findings": total_findings,
            "total_systems": total_systems,
            "total_hostnames": total_hostnames,
            "service_counts": service_counts,
            "recommendations": [],  # TODO
            "asset_vulnerabilities": asset_vulnerabilities,
            "open_ports": open_ports,
            "basic_security": {
                "summary": basic_security_summary,
                "safe_connections": safe_connections_summary,
                "system_specific": system_specific,
            },
            "services": services,
            "ipv6": ["test"],  # TODO
        }


def collect_report_data(
    connector: OctopoesAPIConnector,
    input_ooi_references: List[str],
):
    report_data = {}
    for ooi in [x for x in input_ooi_references if Reference.from_str(x).class_type == ReportData]:
        report_data[ooi] = connector.get(Reference.from_str(ooi)).dict()

    return report_data
