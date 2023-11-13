from dataclasses import dataclass
from datetime import datetime
from logging import getLogger
from typing import Any, Dict

from django.utils.translation import gettext_lazy as _

from octopoes.models import Reference
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.network import IPAddressV4, IPAddressV6
from reports.report_types.definitions import Report

logger = getLogger(__name__)


@dataclass
class System:
    system_types: list
    oois: list


class SystemsReport(Report):
    id = "systems-report"
    name = _("System Report")
    description = _("Combine OOIs into systems")
    plugins = {"required": [], "optional": []}
    input_ooi_types = {Hostname, IPAddressV4, IPAddressV6}
    template_path = "systems_report/report.html"

    def generate_data(self, input_ooi: str, valid_time: datetime) -> Dict[str, Any]:
        systems = []
        reference = Reference.from_str(input_ooi)

        # IMPORTANT: SHOULD BE CHANGED TO PATH QUERIES
        # check record connections of hostname
        if reference.class_type == Hostname:
            ref = Reference.from_str(input_ooi)
            tree = self.octopoes_api_connector.get_tree(
                ref, depth=3, types={IPAddressV4, IPAddressV6}, valid_time=valid_time
            ).store

            for ooi_type, ooi in tree.items():
                a_record_connections = []
                if isinstance(ooi, (IPAddressV4, IPAddressV6)):
                    a_record_connections.append(ooi.primary_key)
                if a_record_connections:
                    a_record_connections.append(input_ooi)
                    systems.append(System(system_types=["Connected by DNS A Record"], oois=a_record_connections))

        # IMPORTANT: SHOULD BE CHANGED TO PATH QUERIES
        if reference.class_type == IPAddressV4 or reference.class_type == IPAddressV6:
            ref = Reference.from_str(input_ooi)
            tree = self.octopoes_api_connector.get_tree(ref, depth=3, types={Hostname}, valid_time=valid_time).store

            for ooi_type, ooi in tree.items():
                a_record_connections = []
                if isinstance(ooi, Hostname):
                    a_record_connections.append(ooi.primary_key)
                if a_record_connections:
                    a_record_connections.append(input_ooi)
                    systems.append(System(system_types=["Connected by DNS A Record"], oois=a_record_connections))

        data = {
            "systems": systems,
            "input_ooi": input_ooi,
        }
        return data
