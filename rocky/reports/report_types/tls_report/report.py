from typing import List

from django.utils.translation import gettext_lazy as _

from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.service import IPService
from reports.report_types.definitions import Report


class TLSReport(Report):
    id = "tls-report"
    name = _("TLS Report")
    required_boefjes: List = []
    optional_boefjes: List = []
    input_ooi_types = {IPService, Hostname}
