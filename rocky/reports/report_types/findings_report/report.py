from datetime import datetime
from logging import getLogger
from typing import Any, Dict

from django.utils.translation import gettext_lazy as _

from octopoes.models import Reference
from octopoes.models.exception import ObjectNotFoundException
from octopoes.models.ooi.findings import Finding
from octopoes.models.types import ALL_TYPES
from reports.report_types.definitions import Report

logger = getLogger(__name__)

TREE_DEPTH = 9


class FindingsReport(Report):
    id = "findings-report"
    name = _("Findings Report")
    description = _("Shows all the finding types and their occurrences.")
    plugins = {"required": [], "optional": []}
    input_ooi_types = ALL_TYPES
    template_path = "findings_report/report.html"

    def generate_data(self, input_ooi: str, valid_time: datetime) -> Dict[str, Any]:
        reference = Reference.from_str(input_ooi)
        findings = []
        finding_types = {}
        severity_totals = {}
        severity_totals_unique = {}

        tree = self.octopoes_api_connector.get_tree(
            reference, depth=TREE_DEPTH, types={Finding}, valid_time=valid_time
        ).store

        for ooi in tree.values():
            if ooi.ooi_type == "Finding":
                findings.append(ooi)

        for finding in findings:
            try:
                finding_type = self.octopoes_api_connector.get(Reference.from_str(finding.finding_type), valid_time)
                severity = finding_type.risk_severity.name.lower()

                if finding_type.id in finding_types:
                    finding_types[finding_type.id]["occurrences"].append(finding)
                    severity_totals[severity] += 1
                else:
                    finding_types[finding_type.id] = {"finding_type": finding_type, "occurrences": [finding]}
                    severity_totals[severity] = 1

                    if severity in severity_totals_unique:
                        severity_totals_unique[severity] += 1
                    else:
                        severity_totals_unique[severity] = 1

            except ObjectNotFoundException:
                logger.error("No Finding Type found for Finding '%s' on date %s.", finding, str(valid_time))

        finding_types = sorted(finding_types.values(), key=lambda x: x["finding_type"].risk_score, reverse=True)

        # Get summary of severity totals
        summary = {
            "severity_totals": severity_totals,
            "severity_totals_unique": severity_totals_unique,
            "total_finding_types": len(finding_types),
            "total_occurrences": len(findings),
        }

        return {"finding_types": finding_types, "summary": summary}
