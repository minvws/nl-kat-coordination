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


class SystemReport(Report):
    id = "systems-report"
    name = _("System Report")
    description = _("Combine ip addresses, hostnames and services into systems.")
    plugins = {"required": [], "optional": []}
    input_ooi_types = {Hostname, IPAddressV4, IPAddressV6}
    template_path = "systems_report/report.html"

    def generate_data(self, input_ooi: str, valid_time: datetime) -> Dict[str, Any]:
        reference = Reference.from_str(input_ooi)
        ips = []

        if reference.class_type == Hostname:
            ips = self.octopoes_api_connector.query(
                "Hostname.<hostname[is ResolvedHostname].address", valid_time, reference
            )
        elif reference.class_type in [IPAddressV4, IPAddressV6]:
            ips = [self.octopoes_api_connector.get(reference)]

        ip_services = {}

        for ip in ips:
            ip_services[str(ip.address)] = {
                "hostnames": [
                    str(x.name)
                    for x in self.octopoes_api_connector.query(
                        "IPAddress.<address[is ResolvedHostname].hostname",
                        valid_time,
                        ip.reference,
                    )
                ],
                "services": [
                    str(x.name)
                    for x in self.octopoes_api_connector.query(
                        "IPAddress.<address[is IPPort].<ip_port [is IPService].service",
                        valid_time,
                        ip.reference,
                    )
                ],
            }

        data = {
            "input_ooi": input_ooi,
            "services": ip_services,
        }
        return data
