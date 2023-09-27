from typing import List

from django.utils.translation import gettext_lazy as _

from octopoes.models import OOI, Reference
from octopoes.models.ooi.dns.records import DNSRecord
from octopoes.models.ooi.dns.zone import Hostname
from reports.report_types.definitions import Report


class DNSReport(Report):
    id = "dns-report"
    name = _("DNS Report")
    description = _("DNS reports focus on domain name system configuration and potential weaknesses.")
    required_boefjes = ["dns-records"]
    optional_boefjes: List = []
    input_ooi_types = {Hostname}
    html_template_path = "dns_report/report.html"

    def generate_data(self, input_ooi: OOI):
        ref = Reference.from_str(input_ooi)
        tree = self.octopoes_api_connector.get_tree(ref, depth=2, types={DNSRecord}).store

        oois = []
        for a, b in tree.items():
            oois.append(a)

        self.octopoes_api_connector.list_origins(result=ref)

        return {"oois": oois}, self.html_template_path
