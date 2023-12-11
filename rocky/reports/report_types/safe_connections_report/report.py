from datetime import datetime
from typing import Any, Dict

from django.utils.translation import gettext_lazy as _

from octopoes.models.ooi.service import IPService
from reports.report_types.definitions import Report

CIPHER_FINDINGS = ["KAT-RECOMMENDATION-BAD-CIPHER", "KAT-MEDIUM-BAD-CIPHER", "KAT-CRITICAL-BAD-CIPHER"]
TREE_DEPTH = 3


class SafeConnectionsRepport(Report):
    id = "safe-connections-report"
    name = _("Safe Connections Report")
    description: str = _("Safe Connections reports ...")
    plugins = {"required": ["testssl-sh-ciphers"], "optional": []}
    input_ooi_types = {IPService}
    template_path = "safe_connections_report/report.html"

    def generate_data(self, input_ooi: str, valid_time: datetime) -> Dict[str, Any]:
        return {
            "input_ooi": input_ooi,
        }
