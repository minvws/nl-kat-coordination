from datetime import datetime
from logging import getLogger
from typing import Any

from django.utils.translation import gettext_lazy as _

from octopoes.models import Reference
from octopoes.models.ooi.findings import Finding, FindingType, RiskLevelSeverity
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

    def generate_data(self, input_ooi: str, valid_time: datetime) -> dict[str, Any]:
        reference = Reference.from_str(input_ooi)
        findings = []
        finding_types: dict[str, Any] = {}
        total_by_severity = {}
        total_by_severity_per_finding_type = {}
        history_cache = {}

        for severity in SEVERITY_OPTIONS:
            total_by_severity[severity] = 0
            total_by_severity_per_finding_type[severity] = 0

        tree = self.octopoes_api_connector.get_tree(
            reference, depth=TREE_DEPTH, types={Finding}, valid_time=valid_time
        ).store

        findings = [ooi for ooi in tree.values() if ooi.ooi_type == "Finding"]
        all_finding_types = self.octopoes_api_connector.list_objects(types={FindingType}, valid_time=valid_time).items

        for finding in findings:
            filter_finding_type = [x for x in all_finding_types if x.id == finding.finding_type.tokenized.id]

            if not filter_finding_type:
                continue

            finding_type = filter_finding_type[0]

            severity = finding_type.risk_severity.name.lower()
            total_by_severity[severity] += 1

            if finding.primary_key not in history_cache:
                history_cache[finding.reference] = self.octopoes_api_connector.get_history(reference=reference)

            time_history = [transaction.valid_time for transaction in history_cache[finding.reference]]

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
