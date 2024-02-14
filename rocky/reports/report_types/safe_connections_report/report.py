from datetime import datetime
from logging import getLogger
from typing import Any

from django.utils.translation import gettext_lazy as _

from octopoes.models import Reference
from octopoes.models.exception import ObjectNotFoundException
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.network import IPAddressV4, IPAddressV6
from reports.report_types.definitions import Report

CIPHER_FINDINGS = ["KAT-RECOMMENDATION-BAD-CIPHER", "KAT-MEDIUM-BAD-CIPHER", "KAT-CRITICAL-BAD-CIPHER"]

logger = getLogger(__name__)


class SafeConnectionsReport(Report):
    id = "safe-connections-report"
    name = _("Safe Connections Report")
    description: str = _("Shows whether the IPService contains safe ciphers.")
    plugins = {"required": ["dns-records", "testssl-sh-ciphers", "nmap"], "optional": []}
    input_ooi_types = {Hostname, IPAddressV4, IPAddressV6}
    template_path = "safe_connections_report/report.html"

    def generate_data(self, input_ooi: str, valid_time: datetime) -> dict[str, Any]:
        try:
            ooi = self.octopoes_api_connector.get(Reference.from_str(input_ooi), valid_time)
        except ObjectNotFoundException as e:
            logger.error("No data found for OOI '%s' on date %s.", str(e), str(valid_time))
            raise ObjectNotFoundException(e)

        if ooi.reference.class_type == Hostname:
            ips = self.octopoes_api_connector.query(
                "Hostname.<hostname[is ResolvedHostname].address", valid_time, ooi.reference
            )
        else:
            ips = [ooi]

        sc_ips = {}
        number_of_ips = len(ips)
        number_of_available = number_of_ips
        finding_types = []

        for ip in ips:
            finding_types = self.octopoes_api_connector.query(
                "IPAddress.<address[is IPPort].<ip_port [is IPService]"
                ".<ip_service [is TLSCipher].<ooi[is Finding].finding_type",
                valid_time,
                ip.reference,
            )

            cipher_findings = list(filter(lambda finding: finding.id in CIPHER_FINDINGS, finding_types))
            finding_types.extend(cipher_findings)

            sc_ips[ip.reference] = cipher_findings
            number_of_available -= 1 if cipher_findings else 0

        return {
            "input_ooi": input_ooi,
            "sc_ips": sc_ips,
            "number_of_available": number_of_available,
            "number_of_ips": number_of_ips,
            "finding_types": finding_types,
        }
