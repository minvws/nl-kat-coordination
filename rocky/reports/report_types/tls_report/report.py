from typing import List

from django.utils.translation import gettext_lazy as _

from octopoes.models import OOI
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.service import IPService
from reports.report_types.definitions import Report


class TLSReport(Report):
    id = "tls-report"
    name = _("TLS Report")
    required_boefjes: List = []
    optional_boefjes: List = []
    input_ooi_types = {IPService, Hostname}
    html_template_path = "tls_report/report.html"

    def generate_data(self, input_ooi: OOI):
        return {"mock_oois": ["mock_ooi2", "mock_ooi3"]}, self.html_template_path
