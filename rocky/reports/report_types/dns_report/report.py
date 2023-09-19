from typing import List

from octopoes.models.ooi.dns.zone import Hostname
from reports.report_types.definitions import Report


class DNSReport(Report):
    name = "dns-report"
    required_boefjes = ["dns-records"]
    optional_boefjes: List = []
    input_ooi_types = {Hostname}
