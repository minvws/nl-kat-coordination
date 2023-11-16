from dataclasses import dataclass
from datetime import datetime
from logging import getLogger
from typing import Any, Dict

from django.utils.translation import gettext_lazy as _

from octopoes.models import Reference
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.network import IPAddressV4, IPAddressV6
from octopoes.models.path import Path
from reports.report_types.definitions import Report

logger = getLogger(__name__)


@dataclass
class System:
    system_types: list
    oois: list


class IPv6Report(Report):
    id = "ipv6-report"
    name = _("IPv6 Report")
    description = _("Check whether hostnames point to ipv6 addresses.")
    plugins = {"required": [], "optional": []}
    input_ooi_types = {Hostname, IPAddressV4, IPAddressV6}
    template_path = "ipv6_report/report.html"

    def generate_data(self, input_ooi: str, valid_time: datetime) -> Dict[str, Any]:
        """
        For hostnames, check whether they point to ipv6 addresses.
        For ip addresses, check all hostnames that point to them, and check whether they point to ipv6 addresses.
        """
        ref = Reference.from_str(input_ooi)
        if ref.class_type == IPAddressV4 or ref.class_type == IPAddressV6:
            path = Path.parse("IPAddress.<address [is ResolvedHostname].hostname")
            hostnames = self.octopoes_api_connector.query(path=path, source=ref, valid_time=valid_time)
            hostnames = [h.reference for h in hostnames]
        else:
            hostnames = [ref]

        results = {}
        for hostname in hostnames:
            path = Path.parse("Hostname.<hostname [is ResolvedHostname].address")
            ips = self.octopoes_api_connector.query(path=path, source=hostname, valid_time=valid_time)

            results = {
                hostname.tokenized.name: any(ip.reference.class_type == IPAddressV6 for ip in ips)
                for hostname in hostnames
            }

        return {"results": results}
