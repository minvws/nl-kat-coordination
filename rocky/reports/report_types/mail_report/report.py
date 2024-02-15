from datetime import datetime
from logging import getLogger
from typing import Any, Dict, List

from django.utils.translation import gettext_lazy as _

from octopoes.models import OOI, Reference
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

    def collect_data(self, input_oois: set[str], valid_time: datetime) -> dict[str, dict[str, Any]]:
        refs = [Reference.from_str(input_ooi) for input_ooi in input_oois]
        hostname_refs_by_input_ooi = {ref: [ref] for ref in refs if ref.class_type == Hostname}
        ip_refs = [ref for ref in refs if ref.class_type in (IPAddressV4, IPAddressV6)]

        for input_ooi, ip_hostnames in self.octopoes_api_connector.query_many(
            "IPAddress.<address[is ResolvedHostname].hostname", valid_time, ip_refs
        ).items():
            hostname_refs_by_input_ooi[input_ooi] = [x.reference for x in ip_hostnames]

        all_hostnames = [h for key, hostnames in hostname_refs_by_input_ooi.items() for h in hostnames]
        measures = self.octopoes_api_connector.query_many(
            "Hostname.<ooi[is Finding].finding_type", valid_time, all_hostnames
        )
        filtered_measures = {
            key: list(filter(lambda finding: finding.id in MAIL_FINDINGS, val)) for key, val in measures.items()
        }

        result = {}
        for input_ooi, hostname_references in hostname_refs_by_input_ooi.items():
            mail_security_measures = {}
            number_of_hostnames = len(hostname_references)
            number_of_spf = number_of_hostnames
            number_of_dmarc = number_of_hostnames
            number_of_dkim = number_of_hostnames

            for hostname in hostname_references:
                measures = filtered_measures[hostname]
                mail_security_measures[hostname] = measures

                number_of_spf -= (
                    1
                    if list(filter(lambda finding: finding.id == "KAT-NO-SPF", mail_security_measures[hostname]))
                    else 0
                )
                number_of_dmarc -= (
                    1
                    if list(filter(lambda finding: finding.id == "KAT-NO-DMARC", mail_security_measures[hostname]))
                    else 0
                )
                number_of_dkim -= (
                    1
                    if list(filter(lambda finding: finding.id == "KAT-NO-DKIM", mail_security_measures[hostname]))
                    else 0
                )

            result[input_ooi] = {
                "input_ooi": input_ooi,
                "finding_types": mail_security_measures,
                "number_of_hostnames": number_of_hostnames,
                "number_of_spf": number_of_spf,
                "number_of_dmarc": number_of_dmarc,
                "number_of_dkim": number_of_dkim,
            }

        return result

    def generate_data(self, input_ooi: str, valid_time: datetime) -> Dict[str, Any]:
        mail_security_measures = {}
        ref = Reference.from_str(input_ooi)

        if ref.class_type == Hostname:
            hostname_references = [ref]
        elif ref.class_type in (IPAddressV4, IPAddressV6):
            hostname_references = self.octopoes_api_connector.query(
                "IPAddress.<address[is ResolvedHostname].hostname", valid_time, ref
            )
        else:
            hostname_references = []

        number_of_hostnames = len(hostname_references)
        number_of_spf = number_of_hostnames
        number_of_dmarc = number_of_hostnames
        number_of_dkim = number_of_hostnames

        for hostname in hostname_references:
            measures = self._get_measures(valid_time, hostname)
            mail_security_measures[hostname] = measures

            number_of_spf -= (
                1 if list(filter(lambda finding: finding.id == "KAT-NO-SPF", mail_security_measures[hostname])) else 0
            )
            number_of_dmarc -= (
                1 if list(filter(lambda finding: finding.id == "KAT-NO-DMARC", mail_security_measures[hostname])) else 0
            )
            number_of_dkim -= (
                1 if list(filter(lambda finding: finding.id == "KAT-NO-DKIM", mail_security_measures[hostname])) else 0
            )

        return {
            "input_ooi": input_ooi,
            "finding_types": mail_security_measures,
            "number_of_hostnames": number_of_hostnames,
            "number_of_spf": number_of_spf,
            "number_of_dmarc": number_of_dmarc,
            "number_of_dkim": number_of_dkim,
        }

    def _get_measures(self, valid_time: datetime, hostname) -> List[OOI]:
        finding_types = self.octopoes_api_connector.query(
            "Hostname.<ooi[is Finding].finding_type", valid_time, hostname
        )

        measures = list(filter(lambda finding: finding.id in MAIL_FINDINGS, finding_types))
        return measures
