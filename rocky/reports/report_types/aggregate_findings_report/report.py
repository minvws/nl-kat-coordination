from datetime import datetime
from logging import getLogger
from typing import Any, Dict, List

from django.utils.translation import gettext_lazy as _

from octopoes.connector.octopoes import OctopoesAPIConnector
from reports.report_types.definitions import Report, ReportType
from reports.report_types.findings_report.report import FindingsReport

logger = getLogger(__name__)


class AggregateFindingsReport(Report):
    id = "aggregate-findings-report"
    name = _("Aggregate Findings Report")
    description = _("Aggregate Findings Report")
    reports = {
        "required": [FindingsReport],
        "optional": [],
    }
    template_path = "aggregate_findings_report/report.html"

    def generate_data(self, input_ooi: str, valid_time: datetime) -> Dict[str, Any]:
        return {}


def aggregate_reports(
    connector: OctopoesAPIConnector,
    input_ooi_references: List[str],
    selected_report_types: List[ReportType],
    valid_time: datetime,
):
    aggregate_report = AggregateFindingsReport(connector)
    report_data = {}

    return aggregate_report, report_data
