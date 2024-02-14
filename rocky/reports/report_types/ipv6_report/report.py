from dataclasses import dataclass
from datetime import datetime
from logging import getLogger
from typing import Any

from django.utils.translation import gettext_lazy as _

from octopoes.models import Reference
from octopoes.models.exception import ObjectNotFoundException
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
    plugins = {"required": ["dns-records"], "optional": []}
    input_ooi_types = {Hostname, IPAddressV4, IPAddressV6}
    template_path = "ipv6_report/report.html"

    def generate_data(self, input_ooi: str, valid_time: datetime) -> dict[str, Any]:
        """
        For hostnames, check whether they point to ipv6 addresses.
        For ip addresses, check all hostnames that point to them, and check whether they point to ipv6 addresses.
        """
        try:
            ooi = self.octopoes_api_connector.get(Reference.from_str(input_ooi), valid_time)
        except ObjectNotFoundException as e:
            logger.error("No data found for OOI '%s' on date %s.", str(e), str(valid_time))
            raise ObjectNotFoundException(e)

        if ooi.reference.class_type == IPAddressV4 or ooi.reference.class_type == IPAddressV6:
            path = Path.parse("IPAddress.<address [is ResolvedHostname].hostname")
            hostnames = self.octopoes_api_connector.query(path=path, source=ooi.reference, valid_time=valid_time)
        else:
            hostnames = [ooi]

        results = {}
        for hostname in hostnames:
            path = Path.parse("Hostname.<hostname [is ResolvedHostname].address")
            ips = self.octopoes_api_connector.query(path=path, source=hostname.reference, valid_time=valid_time)

            results = {
                hostname.name: {"enabled": any(ip.reference.class_type == IPAddressV6 for ip in ips)}
                for hostname in hostnames
            }

        return results
