from datetime import datetime
from logging import getLogger
from typing import Any, Dict, List

from django.utils.translation import gettext_lazy as _

from octopoes.models import Reference
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.network import IPAddressV4, IPAddressV6
from reports.report_types.definitions import Report

logger = getLogger(__name__)


class MailReport(Report):
    id = "mail-report"
    name = _("Mail Report")
    description = _("System specific mail report that focusses on IP addresses and hostnames.")
    plugins = {"required": ["nmap"], "optional": []}
    input_ooi_types = {Hostname, IPAddressV4, IPAddressV6}
    template_path = "mail_report/report.html"

    def generate_data(self, input_ooi: str, valid_time: datetime) -> Dict[str, Any]:
        reference = Reference.from_str(input_ooi)
        hostnames = []
        mail_security_measures = {}

        if reference.class_type == Hostname:
            hostnames = [reference]
            measures = self._get_measures(valid_time, hostnames)
            mail_security_measures = {"hostname": hostnames[0].tokenized.name, "measures": measures}
        elif reference.class_type in (IPAddressV4, IPAddressV6):
            hostnames = self.octopoes_api_connector.query(
                "IPAddress.<address[is ResolvedHostname].hostname", valid_time, reference
            )
            for hostname in hostnames:
                measures = self._get_measures(valid_time, hostname)
                mail_security_measures.update({"hostname": hostname.name, "measures": measures})

        number_of_hostnames = len(hostnames)
        number_of_spf = number_of_hostnames - len(
            list(filter(lambda finding: finding.id == "KAT-NO-SPF", mail_security_measures["measures"]))
        )
        number_of_dmarc = number_of_hostnames - len(
            list(filter(lambda finding: finding.id == "KAT-NO-DMARC", mail_security_measures["measures"]))
        )
        number_of_dkim = number_of_hostnames - len(
            list(filter(lambda finding: finding.id == "KAT-NO-DKIM", mail_security_measures["measures"]))
        )

        return {
            "input_ooi": input_ooi,
            "mail_security_measures": mail_security_measures,
            "number_of_hostnames": number_of_hostnames,
            "number_of_spf": number_of_spf,
            "number_of_dmarc": number_of_dmarc,
            "number_of_dkim": number_of_dkim,
        }

    def _get_measures(self, valid_time: datetime, hostname) -> List[Dict[str, Any]]:
        finding_types = []
        measures = []
        finding_types = self.octopoes_api_connector.query(
            "Hostname.<ooi[is Finding].finding_type", valid_time, hostname
        )
        for finding in finding_types:
            if finding.id == "KAT-NO-SPF" or finding.id == "KAT-NO-DMARC" or finding.id == "KAT-NO-DKIM":
                measures.append(finding)

        return measures
