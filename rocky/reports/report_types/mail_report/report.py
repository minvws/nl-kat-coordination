from datetime import datetime
from logging import getLogger
from typing import Any, Dict, List

from django.utils.translation import gettext_lazy as _

from octopoes.models import OOI, Reference
from octopoes.models.exception import ObjectNotFoundException
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.network import IPAddressV4, IPAddressV6
from reports.report_types.definitions import Report

logger = getLogger(__name__)

MAIL_FINDINGS = ["KAT-NO-SPF", "KAT-NO-DMARC", "KAT-NO-DKIM"]


class MailReport(Report):
    id = "mail-report"
    name = _("Mail Report")
    description = _("System specific mail report that focusses on IP addresses and hostnames.")
    plugins = {"required": ["dns-records"], "optional": []}
    input_ooi_types = {Hostname, IPAddressV4, IPAddressV6}
    template_path = "mail_report/report.html"

    def generate_data(self, input_ooi: str, valid_time: datetime) -> Dict[str, Any]:
        hostnames = []
        finding_types = {}

        try:
            ooi = self.octopoes_api_connector.get(Reference.from_str(input_ooi), valid_time)
        except ObjectNotFoundException as e:
            logger.error("No data found for OOI '%s' on date %s.", str(e), str(valid_time))
            raise ObjectNotFoundException(e)

        if ooi.reference.class_type == Hostname:
            hostnames = [ooi]
        elif ooi.reference.class_type in (IPAddressV4, IPAddressV6):
            hostnames = self.octopoes_api_connector.query(
                "IPAddress.<address[is ResolvedHostname].hostname", valid_time, ooi.reference
            )

        number_of_hostnames = len(hostnames)
        number_of_spf = number_of_hostnames
        number_of_dmarc = number_of_hostnames
        number_of_dkim = number_of_hostnames

        for hostname in hostnames:
            finding_types[hostname.primary_key] = self._get_mail_finding_types(valid_time, hostname.reference)

            number_of_spf -= (
                1
                if list(filter(lambda finding: finding.id == "KAT-NO-SPF", finding_types[hostname.primary_key]))
                else 0
            )
            number_of_dmarc -= (
                1
                if list(filter(lambda finding: finding.id == "KAT-NO-DMARC", finding_types[hostname.primary_key]))
                else 0
            )
            number_of_dkim -= (
                1
                if list(filter(lambda finding: finding.id == "KAT-NO-DKIM", finding_types[hostname.primary_key]))
                else 0
            )

        return {
            "input_ooi": input_ooi,
            "finding_types": finding_types,
            "number_of_hostnames": number_of_hostnames,
            "number_of_spf": number_of_spf,
            "number_of_dmarc": number_of_dmarc,
            "number_of_dkim": number_of_dkim,
        }

    def _get_mail_finding_types(self, valid_time: datetime, hostname) -> List[OOI]:
        finding_types = self.octopoes_api_connector.query(
            "Hostname.<ooi[is Finding].finding_type", valid_time, hostname
        )

        return list(filter(lambda finding: finding.id in MAIL_FINDINGS, finding_types))
