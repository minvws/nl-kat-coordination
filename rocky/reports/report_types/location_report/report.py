from logging import getLogger

from django.utils.translation import gettext_lazy as _

from octopoes.models.ooi.network import IPAddress
from reports.report_types.definitions import Report, ReportPlugins

logger = getLogger(__name__)


class LocationReport(Report):
    id = "location-report"
    name = _("Location Report")
    description = _("Shows the IP address location on a map.")
    plugins: ReportPlugins = {"required": ["maxmind_geoip"], "optional": []}
    input_ooi_types = IPAddress
    template_path = "location_report/report.html"
    label_style = "3-light"
