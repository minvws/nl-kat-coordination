from typing import List

from django.utils.translation import gettext_lazy as _

from octopoes.models import OOI
from octopoes.models.ooi.dns.zone import Hostname
from reports.report_types.definitions import Report


class DNSReport(Report):
    id = "dns-report"
    name = _("DNS Report")
    required_boefjes = ["dns-records"]
    optional_boefjes: List = []
    input_ooi_types = {Hostname}
    html_template_path = "dns_report/report.html"

    def generate_data(self, input_ooi: OOI):
        return {"mock_oois": ["mock_ooi1", "mock_ooi2"]}, self.html_template_path
