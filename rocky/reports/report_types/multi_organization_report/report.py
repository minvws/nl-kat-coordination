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
               "ReportData|org_code": {...},
               "ReportData|org_code_2": {...},
           }
        """

        # TODO:
        #  - Sectornaam
        #  - “Sector X”
        #  - 3 algemene aanbevelingen, 1 systeem
        #  - ...

        return {
            "multi_data": data,
            "organizations": [value["organization_code"] for key, value in data.items()],
        }


def collect_report_data(
    connector: OctopoesAPIConnector,
    input_ooi_references: List[str],
):
    report_data = {}
    for ooi in [x for x in input_ooi_references if Reference.from_str(x).class_type == ReportData]:
        report_data[ooi] = connector.get(Reference.from_str(ooi)).dict()

    return report_data
