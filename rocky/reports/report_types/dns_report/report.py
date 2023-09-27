from logging import getLogger
from typing import List

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
    required_boefjes = ["dns-records", "dnssec"]
    optional_boefjes: List = []
    input_ooi_types = {Hostname}
    html_template_path = "dns_report/report.html"

    def generate_data(self, input_ooi: str):
        ref = Reference.from_str(input_ooi)
        tree = self.octopoes_api_connector.get_tree(ref, depth=3, types={DNSRecord, Finding}).store

        oois = []
        security = {
            "spf": True,
            "dkim": True,
            "dmarc": True,
            "dnssec": True,
        }
        for ooi_type, ooi in tree.items():
            reference = Reference.from_str(ooi)
            logger.error(ooi)
            if isinstance(ooi, DNSRecord):
                origin = self.octopoes_api_connector.list_origins(source=ref, result=reference)
                if origin:
                    oois.append(
                        {
                            "human_readable": reference.human_readable,
                            "content": ooi.value,
                            "origin": origin[0].method,
                        }
                    )
            if isinstance(ooi, Finding):
                if "NO-SPF" in ooi.finding_type.tokenized.id:
                    security["spf"] = False
                if "NO-DKIM" in ooi.finding_type.tokenized.id:
                    security["dkim"] = False
                if "NO-DMARC" in ooi.finding_type.tokenized.id:
                    security["dmarc"] = False
                if "NO-DNSSEC" in ooi.finding_type.tokenized.id:
                    security["dnssec"] = False

        return {"input_ooi": input_ooi, "oois": oois, "security": security}, self.html_template_path
