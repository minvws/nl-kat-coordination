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
            raise

        if ooi.reference.class_type == IPAddressV4 or ooi.reference.class_type == IPAddressV6:
            path = Path.parse("IPAddress.<address [is ResolvedHostname].hostname")
            hostnames = self.octopoes_api_connector.query(path=path, source=ooi.reference, valid_time=valid_time)
        else:
            hostnames = [ooi]

        results = {}
        for hostname in hostnames:
            if ooi.reference.class_type == IPAddressV6:
                return {hostname.name: {"enabled": True} for hostname in hostnames}
            ips = self.octopoes_api_connector.query(
                "Hostname.<hostname [is ResolvedHostname].address", valid_time, hostname.reference
            )

            results = {
                hostname.name: {"enabled": any(ip.reference.class_type == IPAddressV6 for ip in ips)}
                for hostname in hostnames
            }

        return results

    def collect_data(self, input_oois: set[str], valid_time: datetime) -> dict[str, dict[str, Any]]:
        hostnames_by_input_ooi = self.to_hostnames(input_oois, valid_time)
        all_hostnames = [h for key, hostnames in hostnames_by_input_ooi.items() for h in hostnames]

        query = "Hostname.<hostname [is ResolvedHostname].address"
        ips = self.group_by_source(
            self.octopoes_api_connector.query_many(query, valid_time, all_hostnames),
        )

        result = {}
        for input_ooi, hostnames in hostnames_by_input_ooi.items():
            result[input_ooi] = {
                hostname_ref.tokenized.name: {"enabled": any(ip.class_type == IPAddressV6 for ip in ips[input_ooi])}
                for hostname_ref in hostnames
            }

        return result
