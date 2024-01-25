from datetime import datetime
from logging import getLogger
from typing import Any, Dict

from django.utils.translation import gettext_lazy as _

from octopoes.models import Reference
from octopoes.models.ooi.findings import Finding
from octopoes.models.types import ALL_TYPES
from reports.report_types.definitions import Report

logger = getLogger(__name__)

TREE_DEPTH = 9


class FindingsReport(Report):
    id = "findings-report"
    name = _("Findings Report")
    description = _("Findings Report")
    plugins = {"required": [], "optional": []}
    input_ooi_types = ALL_TYPES
    template_path = "findings_report/report.html"

    def generate_data(self, input_ooi: str, valid_time: datetime) -> Dict[str, Any]:
        reference = Reference.from_str(input_ooi)
        findings = []
        results = {}

        tree = self.octopoes_api_connector.get_tree(
            reference, depth=TREE_DEPTH, types={Finding}, valid_time=valid_time
        ).store
        for pk, ooi in tree.items():
            if ooi.ooi_type == "Finding":
                findings.append(ooi)

        for finding in findings:
            finding_types = self.octopoes_api_connector.query(
                "Finding.finding_type", valid_time, Reference.from_str(finding)
            )

            if finding_types:
                finding_type = finding_types[0]

                if finding_type.id in results:
                    results[finding_type.id]["occurrences"].append(finding)
                else:
                    results[finding_type.id] = {"finding_type": finding_type, "occurrences": [finding]}

        return results
