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
        rpki_summary = {}
        ipv6 = {}
        recommendation_counts = {}
        organization_metrics = {}

        for organization, report_data in data.items():
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
                    "vulnerabilities": {k: v["cvss"]["score"] for k, v in vulnerabilities["vulnerabilities"].items()},
                    "organisation": report_data["organization_code"],
                    "services": aggregate_data["systems"]["services"][system]["services"],
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
                    system_specific[service] = {"checks": {}, "total": 0}

                system_specific[service]["total"] += summary["system_specific"]["total"]
                for title, count in summary["system_specific"]["checks"].items():
                    if title not in system_specific[service]["checks"]:
                        system_specific[service]["checks"][title] = 0

                    system_specific[service]["checks"][title] += count

            for service, rpki in aggregate_data["basic_security"]["rpki"].items():
                if service not in rpki_summary:
                    rpki_summary[service] = {
                        "number_of_available": 0,
                        "number_of_ips": 0,
                        "number_of_valid": 0,
                        "rpki_ips": True,  # To trigger rendering (not the best solution)
                    }

                rpki_summary[service]["number_of_available"] += rpki["number_of_available"]
                rpki_summary[service]["number_of_ips"] += rpki["number_of_ips"]
                rpki_summary[service]["number_of_valid"] += rpki["number_of_valid"]

            for system, info in aggregate_data["ipv6"].items():
                for system_type in info["systems"]:
                    if system_type not in ipv6:
                        ipv6[system_type] = {"total": 0, "enabled": 0}

                    ipv6[system_type]["total"] += 1
                    ipv6[system_type]["enabled"] += info["enabled"]

            for recommendation, count in aggregate_data["recommendation_counts"].items():
                if recommendation == "null":
                    continue

                if recommendation not in recommendation_counts:
                    recommendation_counts[recommendation] = 0

                recommendation_counts[recommendation] += 1

            # Get metrics per organization for best and worst security score
            ## Safe Connections
            is_check_compliant = (
                safe_connections_summary["number_of_available"] == safe_connections_summary["number_of_ips"]
            )
            organization_metrics.setdefault("Safe Ciphers", {})[organization] = is_check_compliant

            ## System Specific
            for value in system_specific.values():
                for check, count in value["checks"].items():
                    is_check_compliant = count == value["total"]
                    organization_metrics.setdefault(check, {}).setdefault(organization, is_check_compliant)
                    if organization in organization_metrics[check] and not is_check_compliant:  # to avoid duplicates
                        organization_metrics[check][organization] = is_check_compliant

            ## RPKI
            rpki_available_compliant = all(
                value["number_of_available"] == value["number_of_ips"] for value in rpki_summary.values()
            )
            rpki_valid_compliant = all(
                value["number_of_valid"] == value["number_of_ips"] for value in rpki_summary.values()
            )
            organization_metrics.setdefault("RPKI Available", {})[organization] = rpki_available_compliant
            organization_metrics.setdefault("RPKI Valid", {})[organization] = rpki_valid_compliant

        # Calculate security score
        for check, results in organization_metrics.items():
            organization_metrics[check]["score"] = sum(results.values()) / len(results) * 100
        best_score = max(organization_metrics, key=lambda x: organization_metrics[x]["score"])
        worst_score = min(organization_metrics, key=lambda x: organization_metrics[x]["score"])

        system_vulnerabilities = {}
        system_vulnerability_totals = {}

        for asset_vulnerability in asset_vulnerabilities:
            for vulnerability, score in asset_vulnerability["vulnerabilities"].items():
                if vulnerability not in system_vulnerabilities:
                    system_vulnerabilities[vulnerability] = {"cvss": score}

                for service in asset_vulnerability["services"]:
                    if service not in system_vulnerabilities[vulnerability]:
                        system_vulnerabilities[vulnerability][service] = 0

                    if service not in system_vulnerability_totals:
                        system_vulnerability_totals[service] = 0

                    system_vulnerabilities[vulnerability][service] += 1
                    system_vulnerability_totals[service] += 1

        system_vulnerabilities = sorted(system_vulnerabilities.items(), key=lambda x: x[1]["cvss"] or 0, reverse=True)

        return {
            "multi_data": data,
            "organizations": [value["organization_code"] for key, value in data.items()],
            "tags": tags,
            # Average score over organizations
            "basic_security_score": round(
                sum(x["compliant"] / x["total"] if x["total"] > 0 else 0 for x in basic_securities)
                / len(basic_securities)
                * 100
            ),
            "total_critical_vulnerabilities": total_critical_vulnerabilities,
            "total_findings": total_findings,
            "total_systems": total_systems,
            "total_hostnames": total_hostnames,
            "service_counts": service_counts,
            "asset_vulnerabilities": asset_vulnerabilities,
            "system_vulnerabilities": dict(system_vulnerabilities),
            "system_vulnerability_totals": system_vulnerability_totals,
            "open_ports": open_ports,
            "basic_security": {
                "summary": basic_security_summary,
                "safe_connections": safe_connections_summary,
                "system_specific": system_specific,
                "rpki": rpki_summary,
            },
            "services": services,
            "recommendation_counts": recommendation_counts,
            "best_scoring": best_score,
            "worst_scoring": worst_score,
            "ipv6": ipv6,
        }


def collect_report_data(
    connector: OctopoesAPIConnector,
    input_ooi_references: List[str],
):
    report_data = {}
    for ooi in [x for x in input_ooi_references if Reference.from_str(x).class_type == ReportData]:
        report_data[ooi] = connector.get(Reference.from_str(ooi)).dict()

    return report_data
