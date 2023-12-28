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

        for report_data in data.values():
            basic_security = {"compliant": 0, "total": 0}

            for tag in report_data["organization_tags"]:
                if tag not in tags:
                    tags[tag] = []

                tags[tag].append(report_data["organization_code"])

            total_critical_vulnerabilities += report_data["data"]["post_processed_data"]["summary"][
                "Critical vulnerabilities"
            ]
            total_findings += report_data["data"]["post_processed_data"]["total_findings"]
            total_systems += report_data["data"]["post_processed_data"]["total_systems"]
            total_hostnames += report_data["data"]["post_processed_data"]["total_hostnames"]

            for compliance in report_data["data"]["post_processed_data"]["basic_security"]["summary"].values():
                for counts in compliance.values():
                    basic_security["total"] += counts["total"]
                    basic_security["compliant"] += counts["number_of_compliant"]

            basic_securities.append(basic_security)

        # TODO:
        #  - Sectornaam
        #  - “Sector X”
        #  - Benchmark comparison X ?
        #  - Best scoring security checks
        #  - Lowest organisations in report
        #  - Lowest organisations in report per tag
        #  - Most common vulnerabilities

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
            "recommendations": [],  # TODO
        }


def collect_report_data(
    connector: OctopoesAPIConnector,
    input_ooi_references: List[str],
):
    report_data = {}
    for ooi in [x for x in input_ooi_references if Reference.from_str(x).class_type == ReportData]:
        report_data[ooi] = connector.get(Reference.from_str(ooi)).dict()

    return report_data
