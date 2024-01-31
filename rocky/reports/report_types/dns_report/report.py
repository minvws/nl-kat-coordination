from datetime import datetime
from logging import getLogger
from typing import Any, Dict

from django.utils.translation import gettext_lazy as _

from octopoes.models import Reference
from octopoes.models.ooi.dns.records import DNSRecord
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

        records = []
        security = {
            "spf": True,
            "dkim": True,
            "dmarc": True,
            "dnssec": True,
            "caa": True,
        }
        for ooi_type, ooi in tree.items():
            if isinstance(ooi, Finding):
                if "NO-SPF" in ooi.finding_type.tokenized.id:
                    security["spf"] = False
                if "NO-DKIM" in ooi.finding_type.tokenized.id:
                    security["dkim"] = False
                if "NO-DMARC" in ooi.finding_type.tokenized.id:
                    security["dmarc"] = False
                if "NO-DNSSEC" in ooi.finding_type.tokenized.id:
                    security["dnssec"] = False
                if "NO-CAA" in ooi.finding_type.tokenized.id:
                    security["caa"] = False
            elif isinstance(ooi, DNSRecord):
                records.append(
                    {
                        "type": ooi.dns_record_type,
                        "ttl": round(ooi.ttl / 60),
                        "name": ooi.hostname.tokenized.name,
                        "content": ooi.value,
                    }
                )

        return {
            "input_ooi": input_ooi,
            "records": records,
            "security": security,
        }
