from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from logging import getLogger

from django.utils.translation import gettext_lazy as _

from octopoes.models.ooi.network import IPAddressV4, IPAddressV6
from reports.report_types.definitions import Report, ReportPlugins

logger = getLogger(__name__)


@dataclass
class System:
    system_types: list
    oois: list


class LocationReport(Report):
    id = "location-report"
    name = _("Location Report")
    description = _("Shows the location of the found IP addresses.")
    plugins: ReportPlugins = {"required": [], "optional": []}
    input_ooi_types = {IPAddressV4, IPAddressV6}
    template_path = "location_report/report.html"
    label_style = "4-light"

    def collect_data(self, input_oois: Iterable[str], valid_time: datetime) -> dict:
        """
        For IP addresses, get the geolocation.
        """
        result: dict = {}

        return result
