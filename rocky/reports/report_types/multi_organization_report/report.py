from datetime import datetime
from logging import getLogger
from typing import Any, Dict

from django.utils.translation import gettext_lazy as _

from octopoes.models.ooi.reports import ReportData
from reports.report_types.definitions import Report

logger = getLogger(__name__)


class MultiOrganizationReport(Report):
    id = "multi-organization-report"
    name = _("Multi Organization Report")
    description = _("Multi Organization Report")
    plugins = {"required": [], "optional": []}
    input_ooi_types = {ReportData}
    template_path = "multi_organization_report/report.html"

    def generate_data(self, input_ooi: str, valid_time: datetime) -> Dict[str, Any]:
        return {}
