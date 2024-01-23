from datetime import datetime
from logging import getLogger
from typing import Any, Dict

from django.utils.translation import gettext_lazy as _

from octopoes.models import Reference
from octopoes.models.ooi.dns.zone import Hostname
from reports.report_types.definitions import Report

logger = getLogger(__name__)


class FindingsReport(Report):
    id = "findings-report"
    name = _("Findings Report")
    description = _("Findings Report")
    template_path = "findings_report/report.html"

    def generate_data(self, input_ooi: str, valid_time: datetime) -> Dict[str, Any]:
        reference = Reference.from_str(input_ooi)
        if reference.class_type == Hostname:
            ips = self.octopoes_api_connector.query(
                "Hostname.<hostname[is ResolvedHostname].address", valid_time, reference
            )
        else:
            ips = [self.octopoes_api_connector.get(reference)]

        for ip in ips:
            finding_types = self.octopoes_api_connector.query(
                "IPAddress.<ooi[is Finding].finding_type", valid_time, ip.reference
            )

        return {"finding_types": finding_types}
