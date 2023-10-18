from datetime import datetime
from logging import getLogger
from typing import Any, Dict

from django.utils.translation import gettext_lazy as _

from octopoes.models import Reference
from octopoes.models.ooi.dns.records import DNSAAAARecord, DNSARecord, DNSRecord
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.findings import Finding
from reports.report_types.definitions import Report

logger = getLogger(__name__)


class DNSReport(Report):
    id = "dns-report"
    name = _("DNS Report")
    description = _("DNS reports focus on domain name system configuration and potential weaknesses.")
    plugins = {"required": ["dns-records", "dns-sec"], "optional": ["dns-zone"]}
    input_ooi_types = {Hostname}
    template_path = "dns_report/report.html"

    def generate_data(self, input_ooi: str, valid_time: datetime) -> Dict[str, Any]:
        ref = Reference.from_str(input_ooi)
        tree = self.octopoes_api_connector.get_tree(
            ref, depth=3, types={DNSRecord, Finding}, valid_time=valid_time
        ).store

        other_records = []
        security = {
            "spf": True,
            "dkim": True,
            "dmarc": True,
            "dnssec": True,
        }
        ipv4 = []
        ipv6 = []
        for ooi_type, ooi in tree.items():
            reference = Reference.from_str(ooi)
            if isinstance(ooi, DNSARecord):
                if ref.tokenized.name == ooi.hostname.tokenized.name:
                    ipv4.append(ooi.value)
            elif isinstance(ooi, DNSAAAARecord):
                if ref.tokenized.name == ooi.hostname.tokenized.name:
                    ipv6.append(ooi.value)
            elif isinstance(ooi, DNSRecord):
                origin = self.octopoes_api_connector.list_origins(source=ref, result=reference, valid_time=valid_time)
                if origin:
                    other_records.append(
                        {
                            "human_readable": reference.human_readable,
                            "content": ooi.value,
                            "origin": origin[0].method,
                        }
                    )
            elif isinstance(ooi, Finding):
                if "NO-SPF" in ooi.finding_type.tokenized.id:
                    security["spf"] = False
                if "NO-DKIM" in ooi.finding_type.tokenized.id:
                    security["dkim"] = False
                if "NO-DMARC" in ooi.finding_type.tokenized.id:
                    security["dmarc"] = False
                if "NO-DNSSEC" in ooi.finding_type.tokenized.id:
                    security["dnssec"] = False

        enough_ipv6_webservers = len(ipv6) >= 2

        return {
            "input_ooi": input_ooi,
            "other_records": other_records,
            "security": security,
            "ipv4": ipv4,
            "ipv6": ipv6,
            "enough_ipv6_webservers": enough_ipv6_webservers,
        }
