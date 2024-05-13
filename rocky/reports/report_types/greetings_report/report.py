from datetime import datetime
from logging import getLogger
from typing import Any

from django.utils.translation import gettext_lazy as _

from octopoes.models.ooi.greeting import Greeting
from octopoes.models.ooi.network import IPAddressV4, IPAddressV6
from reports.report_types.definitions import Report

logger = getLogger(__name__)


class GreetingsReport(Report):
    id = "greetings-report"
    name = _("Greetings report")
    description = _("Makes a nice report about the selected greeting objects")
    plugins = {"required": [], "optional": []}
    input_ooi_types = {Greeting, IPAddressV4, IPAddressV6}
    template_path = "greetings_report/report.html"

    def generate_data(self, input_ooi: str, valid_time: datetime) -> dict[str, Any]:
        return {"input_ooi": input_ooi}
