from typing import List

from octopoes.models.ooi.service import IPService
from reports.report_types.definitions import Report


class TLSReport(Report):
    name = "tls-report"
    required_boefjes: List = []
    optional_boefjes: List = []
    input_ooi_types = {IPService}
