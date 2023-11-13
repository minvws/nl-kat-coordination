from datetime import datetime
from logging import getLogger
from typing import Any, Dict

from django.utils.translation import gettext_lazy as _

from octopoes.models import Reference
from octopoes.models.ooi.network import IPAddressV4, IPAddressV6, IPPort
from reports.report_types.definitions import Report

logger = getLogger(__name__)


class OpenPortsReport(Report):
    id = "open-ports-report"
    name = _("Open Ports Report")
    description = _("Find open ports of IP addresses")
    plugins = {"required": [], "optional": []}
    input_ooi_types = {IPAddressV4, IPAddressV6}
    template_path = "open_ports_report/report.html"

    def generate_data(self, input_ooi: str, valid_time: datetime) -> Dict[str, Any]:
        data = {}
        ref = Reference.from_str(input_ooi)
        tree = self.octopoes_api_connector.get_tree(ref, depth=3, types={IPPort}, valid_time=valid_time).store
        for ooi_type, ooi in tree.items():
            reference = Reference.from_str(ooi)
            if isinstance(ooi, IPPort):
                origin = self.octopoes_api_connector.list_origins(result=reference, valid_time=valid_time)
                nmap_origin = [o for o in origin if o.method == "kat_nmap_normalize"]
                found_by_nmap = len(nmap_origin) > 0
                data[reference.tokenized.port] = found_by_nmap
        return data
