from datetime import datetime
from logging import getLogger
from typing import Any, Dict

from django.utils.translation import gettext_lazy as _

from reports.report_types.definitions import Report

logger = getLogger(__name__)


class FindingsReport(Report):
    id = "findings-report"
    name = _("Findings Report")
    description = _("Findings Report")
    template_path = "findings_report/report.html"

    def generate_data(self, input_ooi: str, valid_time: datetime) -> Dict[str, Any]:
        return {}
