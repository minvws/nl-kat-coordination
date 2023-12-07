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


class MailReport(Report):
    id = "mail-report"
    name = _("Mail Report")
    description = _("System specific mail report that focusses on IP addresses and hostnames.")
    plugins = {"required": ["nmap"], "optional": []}
    input_ooi_types = {Hostname, IPAddressV4, IPAddressV6}
    template_path = "mail_report/report.html"

    def generate_data(self, input_ooi: str, valid_time: datetime) -> Dict[str, Any]:
        reference = Reference.from_str(input_ooi)
        finding_types = []
        mail_security_measures = {}

        if reference.class_type == Hostname:
            finding_types = self.octopoes_api_connector.query(
                "Hostname.<ooi[is Finding].finding_type", valid_time, reference
            )
        elif reference.class_type in (IPAddressV4, IPAddressV6):
            finding_types = self.octopoes_api_connector.query(
                "IPAddress.<address[is ResolvedHostname].hostname.<ooi[is Finding].finding_type", valid_time, reference
            )

        finding_types_ids = [x.tokenized.id for x in finding_types]

        has_spf = "KAT-NO-SPF" in finding_types_ids
        has_dmarc = "KAT-NO-DMARC" in finding_types_ids
        has_dkim = "KAT-NO-DKIM" in finding_types_ids

        mail_security_measures = {"has_spf": has_spf, "has_dmarc": has_dmarc, "has_dkim": has_dkim}

        return {
            "input_ooi": input_ooi,
            "mail_security_measures": mail_security_measures,
        }
