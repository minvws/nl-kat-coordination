from datetime import datetime
from logging import getLogger
from typing import Any

from django.utils.translation import gettext_lazy as _

from octopoes.models import Reference
from octopoes.models.exception import ObjectNotFoundException
from octopoes.models.ooi.findings import Finding, RiskLevelSeverity
from octopoes.models.types import ALL_TYPES
from reports.report_types.definitions import Report, ReportPlugins

logger = getLogger(__name__)

TREE_DEPTH = 9
SEVERITY_OPTIONS = [severity.value for severity in RiskLevelSeverity]


class FindingsReport(Report):
    id = "findings-report"
    name = _("Findings Report")
    description = _("Shows all the finding types and their occurrences.")
    plugins: ReportPlugins = {"required": [], "optional": []}
    input_ooi_types = ALL_TYPES
    template_path = "findings_report/report.html"
    label_style = "tags-color-3-light"

    def get_finding_valid_time_history(self, reference: Reference) -> list[datetime]:
        transaction_record = self.octopoes_api_connector.get_history(reference=reference)
        valid_time_history = [transaction.valid_time for transaction in transaction_record]
        return valid_time_history

    def generate_data(self, input_ooi: str, valid_time: datetime) -> dict[str, Any]:
        reference = Reference.from_str(input_ooi)
        findings = []
        finding_types: dict[str, Any] = {}
        total_by_severity = {}
        total_by_severity_per_finding_type = {}

        for severity in SEVERITY_OPTIONS:
            total_by_severity[severity] = 0
            total_by_severity_per_finding_type[severity] = 0

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
                total_by_severity[severity] += 1

                time_history = self.get_finding_valid_time_history(finding.reference)

                if time_history:
                    first_seen = str(time_history[0])
                else:
                    first_seen = "-"

                finding_dict = {"finding": finding, "first_seen": first_seen}

                if finding_type.id in finding_types:
                    finding_types[finding_type.id]["occurrences"].append(finding_dict)
                else:
                    finding_types[finding_type.id] = {"finding_type": finding_type, "occurrences": [finding_dict]}
                    total_by_severity_per_finding_type[severity] += 1

            except ObjectNotFoundException:
                logger.error("No Finding Type found for Finding '%s' on date %s.", finding, str(valid_time))

        sorted_finding_types: list[Any] = sorted(
            finding_types.values(), key=lambda x: x["finding_type"].risk_score or 0, reverse=True
        )

        summary = {
            "total_by_severity": total_by_severity,
            "total_by_severity_per_finding_type": total_by_severity_per_finding_type,
            "total_finding_types": len(sorted_finding_types),
            "total_occurrences": sum(total_by_severity.values()),
        }

        return {"finding_types": sorted_finding_types, "summary": summary}
