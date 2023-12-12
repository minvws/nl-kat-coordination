from dataclasses import dataclass
from datetime import datetime
from logging import getLogger
from typing import Any, Dict, List

from django.utils.translation import gettext_lazy as _

from octopoes.models import Reference
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.network import IPAddressV4, IPAddressV6
from reports.report_types.definitions import Report

logger = getLogger(__name__)


@dataclass
class WebCheck:
    has_csp: bool = False
    has_no_csp_vulnerabilities: bool = False
    redirects_http_https: bool = False
    offers_https: bool = False
    has_security_txt: bool = False
    no_uncommon_ports: bool = False
    has_certificates: bool = False
    certificates_not_expired: bool = False
    certificates_not_expiring_soon: bool = False


@dataclass
class WebChecks:
    checks: List[WebCheck]

    @property
    def has_csp(self):
        return sum([check.has_csp for check in self.checks])

    @property
    def has_csp_vulnerabilities(self):
        return sum([check.has_no_csp_vulnerabilities for check in self.checks])

    @property
    def redirects_http_https(self):
        return sum([check.redirects_http_https for check in self.checks])

    @property
    def offers_https(self):
        return sum([check.offers_https for check in self.checks])

    @property
    def has_security_txt(self):
        return sum([check.has_security_txt for check in self.checks])

    @property
    def no_uncommon_ports(self):
        return sum([check.no_uncommon_ports for check in self.checks])

    @property
    def has_certificates(self):
        return sum([check.has_certificates for check in self.checks])

    @property
    def certificates_not_expired(self):
        return sum([check.certificates_not_expired for check in self.checks])

    @property
    def certificates_not_expiring_soon(self):
        return sum([check.certificates_not_expiring_soon for check in self.checks])

    def __len__(self):
        return len(self.checks)


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

        web_checks = WebChecks(checks=[])
        finding_types = []

        for web_hostname in hostnames:
            check = WebCheck()
            resource_finding_types = self.octopoes_api_connector.query(
                "Hostname.<hostname[is Website].<website[is HTTPResource].<ooi[is Finding].finding_type",
                valid_time,
                web_hostname.reference,
            )
            check.has_csp = "KAT-NO-CSP" not in [x.id for x in resource_finding_types]
            header_finding_types = self.octopoes_api_connector.query(
                "Hostname.<hostname[is Website].<website[is HTTPResource].<resource[is HTTPHeader].<ooi[is Finding].finding_type",
                valid_time,
                web_hostname.reference,
            )
            check.has_no_csp_vulnerabilities = not check.has_csp or "KAT-CSP-VULNERABILITIES" not in [
                x.id for x in header_finding_types
            ]
            url_finding_types = self.octopoes_api_connector.query(
                "Hostname.<netloc[is HostnameHTTPURL].<ooi[is Finding].finding_type",
                valid_time,
                web_hostname.reference,
            )
            check.redirects_http_https = "KAT-NO-HTTPS-REDIRECT" not in [x.id for x in url_finding_types]
            website_finding_types = self.octopoes_api_connector.query(
                "Hostname.<hostname[is Website].<ooi[is Finding].finding_type",
                valid_time,
                web_hostname.reference,
            )
            check.offers_https = "KAT-NO-CERTIFICATE" not in [x.id for x in website_finding_types]
            check.has_security_txt = bool(
                self.octopoes_api_connector.query(
                    "Hostname.<hostname[is Website].<website[is SecurityTXT]",
                    valid_time,
                    web_hostname.reference,
                )
            )

            port_finding_types = self.octopoes_api_connector.query(
                "Hostname.<hostname[is ResolvedHostname].address.<address[is IPPort].<ooi[is Finding].finding_type",
                valid_time,
                web_hostname.reference,
            )
            check.no_uncommon_ports = not (
                "KAT-UNCOMMON-OPEN-PORT" in [x.id for x in port_finding_types]
                or "KAT-OPEN-SYSADMIN-PORT" in [x.id for x in port_finding_types]
                or "KAT-OPEN-DATABASE-PORT" in [x.id for x in port_finding_types]
            )
            check.has_certificates = bool(
                self.octopoes_api_connector.query(
                    "Hostname.<hostname[is Website].certificate",
                    valid_time,
                    web_hostname.reference,
                )
            )

            certificate_finding_types = self.octopoes_api_connector.query(
                "Hostname.<hostname[is Website].certificate.<ooi[is Finding].finding_type",
                valid_time,
                web_hostname.reference,
            )
            check.certificates_not_expired = not check.has_certificates or "KAT-CERTIFICATE-EXPIRED" not in [
                x.id for x in certificate_finding_types
            ]
            check.certificates_not_expiring_soon = not check.has_certificates or "KAT-CERTIFICATE-EXPIRING-SOON" in [
                x.id for x in certificate_finding_types
            ]

            web_checks.checks.append(check)
            finding_types.extend(
                resource_finding_types
                + header_finding_types
                + url_finding_types
                + website_finding_types
                + port_finding_types
                + certificate_finding_types
            )

        return {
            "input_ooi": input_ooi,
            "web_checks": web_checks,
            "finding_types": finding_types,
        }
