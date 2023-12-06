from datetime import datetime
from logging import getLogger
from typing import Any, Dict

from django.utils.translation import gettext_lazy as _

from octopoes.models import Reference
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.network import IPAddressV4, IPAddressV6
from reports.report_types.definitions import Report

logger = getLogger(__name__)


class WebSystemReport(Report):
    id = "web-system-report"
    name = _("Web System Report")
    description = _("Web system reports check web systems on basic security standards.")
    plugins = {
        "required": [
            "nmap",
            "dns-records",
            "testssl-sh-ciphers",
            "ssl-version",
            "ssl-certificates",
            "webpage-analysis",
        ],
        "optional": [],
    }
    input_ooi_types = {Hostname, IPAddressV4, IPAddressV6}
    template_path = "web_system_report/report.html"

    def generate_data(self, input_ooi: str, valid_time: datetime) -> Dict[str, Any]:
        reference = Reference.from_str(input_ooi)
        hostnames = []

        if reference.class_type == Hostname:
            hostnames = [self.octopoes_api_connector.get(reference)]

        elif reference.class_type in (IPAddressV4, IPAddressV6):
            hostnames = self.octopoes_api_connector.query(
                "Hostname.<hostname[is ResolvedHostname].address", valid_time, reference
            )

        web_hostnames = []
        has_website_query = "Hostname.<hostname [is Website]"

        for hostname in hostnames:
            if bool(self.octopoes_api_connector.query(has_website_query, valid_time, hostname.reference)):
                web_hostnames.append(hostname)

        for web_hostname in web_hostnames:
            self.octopoes_api_connector.query(
                "Hostname.<ooi[is Finding].finding_type",
                valid_time,
                web_hostname.reference,
            )
            self.octopoes_api_connector.query(
                "Hostname.<hostname[is Website].<website[is HTTPResource].<ooi[is Finding].finding_type",
                valid_time,
                web_hostname.reference,
            )
            self.octopoes_api_connector.query(
                "Hostname.<netloc[is HostnameHTTPURL].<ooi[is Finding].finding_type",
                valid_time,
                web_hostname.reference,
            )
            self.octopoes_api_connector.query(
                "Hostname.<hostname[is Website].<ooi[is Finding].finding_type",
                valid_time,
                web_hostname.reference,
            )
            self.octopoes_api_connector.query(
                "Hostname.<hostname[is Website].<website[is SecurityTXT]",
                valid_time,
                web_hostname.reference,
            )
            self.octopoes_api_connector.query(
                "Hostname.<hostname[is ResolvedHostname].address.<address[is IPPort]",
                valid_time,
                web_hostname.reference,
            )
            self.octopoes_api_connector.query(
                "Hostname.<hostname[is Website].certificate.<ooi[is Finding].finding_type",
                valid_time,
                web_hostname.reference,
            )

        return {
            "input_ooi": input_ooi,
            "services": web_hostnames,
        }
