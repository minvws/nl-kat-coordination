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


class OpenPortsReport(Report):
    id = "open-ports-report"
    name = _("Open Ports Report")
    description = _("Find open ports of IP addresses")
    plugins = {"required": ["nmap"], "optional": ["shodan", "nmap-udp", "nmap-ports", "nmap-ip-range", "masscan"]}
    input_ooi_types = {Hostname, IPAddressV4, IPAddressV6}
    template_path = "open_ports_report/report.html"

    def generate_data(self, input_ooi: str, valid_time: datetime) -> Dict[str, Any]:
        ref = Reference.from_str(input_ooi)
        if ref.class_type == Hostname:
            path = Path.parse("Hostname.<hostname [is ResolvedHostname].address")
            ips = self.octopoes_api_connector.query(path=path, source=ref, valid_time=valid_time)
            if not ips:
                return {}
            references = [ip.reference for ip in ips]
        else:
            references = [ref]

        results = {}
        for ref in references:
            ports_path = Path.parse("IPAddress.<address [is IPPort]")
            ports = self.octopoes_api_connector.query(path=ports_path, source=ref, valid_time=valid_time)

            hostnames_path = Path.parse("IPAddress.<address [is ResolvedHostname].hostname")
            hostnames = self.octopoes_api_connector.query(path=hostnames_path, source=ref, valid_time=valid_time)
            hostnames = [h.name for h in hostnames]

            port_numbers = {}

            for port in ports:
                origin = self.octopoes_api_connector.list_origins(result=port.reference, valid_time=valid_time)
                found_by_openkat = bool(
                    [o for o in origin if o.method in ("kat_nmap_normalize", "kat_masscan_normalize")]
                )
                port_numbers[port.port] = found_by_openkat

            results[ref.tokenized.address] = {"ports": port_numbers, "hostnames": hostnames}

        return results
