from datetime import datetime
from logging import getLogger
from typing import Any, Dict

from django.utils.translation import gettext_lazy as _

from reports.report_types.definitions import Report

logger = getLogger(__name__)


class AggregateFindingsReport(Report):
    id = "aggregate-findings-report"
    name = _("Aggregate Findings Report")
    description = _("Aggregate Findings Report")
    template_path = "aggregate_findings_report/report.html"

    def generate_data(self, input_ooi: str, valid_time: datetime) -> Dict[str, Any]:
        return {}
