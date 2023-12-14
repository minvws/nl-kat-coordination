from dataclasses import dataclass, field
from datetime import datetime
from logging import getLogger
from typing import Any, Dict, List

from django.utils.translation import gettext_lazy as _

from octopoes.models import Reference
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.findings import RiskLevelSeverity
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
    checks: List[WebCheck] = field(default_factory=list)

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
            "security_txt_downloader",
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
                "IPAddress.<address[is ResolvedHostname].hostname", valid_time, reference
            )

        web_checks = WebChecks()
        finding_types = {}

        for web_hostname in hostnames:
            check = WebCheck()
            csp_finding_types = [
                x
                for x in self.octopoes_api_connector.query(
                    "Hostname.<hostname[is Website].<website[is HTTPResource].<ooi[is Finding].finding_type",
                    valid_time,
                    web_hostname.reference,
                )
                if x.id == "KAT-NO-CSP"
            ]
            check.has_csp = not any(csp_finding_types)
            csp_vulnerabilities_finding_types = [
                x
                for x in self.octopoes_api_connector.query(
                    "Hostname.<hostname[is Website].<website[is HTTPResource].<resource[is HTTPHeader]."
                    "<ooi[is Finding].finding_type",
                    valid_time,
                    web_hostname.reference,
                )
                if x.id == "KAT-CSP-VULNERABILITIES"
            ]
            check.has_no_csp_vulnerabilities = check.has_csp and not any(csp_vulnerabilities_finding_types)
            url_finding_types = [
                x
                for x in self.octopoes_api_connector.query(
                    "Hostname.<netloc[is HostnameHTTPURL].<ooi[is Finding].finding_type",
                    valid_time,
                    web_hostname.reference,
                )
                if x.id == "KAT-NO-HTTPS-REDIRECT"
            ]
            check.redirects_http_https = not any(url_finding_types)

            no_certificate_finding_types = [
                x
                for x in self.octopoes_api_connector.query(
                    "Hostname.<hostname[is Website].<ooi[is Finding].finding_type",
                    valid_time,
                    web_hostname.reference,
                )
                if x.id == "KAT-NO-CERTIFICATE"
            ]
            check.offers_https = not any(no_certificate_finding_types)
            check.has_security_txt = bool(
                self.octopoes_api_connector.query(
                    "Hostname.<hostname[is Website].<website[is SecurityTXT]",
                    valid_time,
                    web_hostname.reference,
                )
            )

            port_finding_types = [
                x
                for x in self.octopoes_api_connector.query(
                    "Hostname.<hostname[is ResolvedHostname].address.<address[is IPPort].<ooi[is Finding].finding_type",
                    valid_time,
                    web_hostname.reference,
                )
                if x.id in ["KAT-UNCOMMON-OPEN-PORT", "KAT-OPEN-SYSADMIN-PORT", "KAT-OPEN-DATABASE-PORT"]
            ]
            check.no_uncommon_ports = not any(port_finding_types)
            check.has_certificates = check.offers_https

            certificate_finding_types = [
                x
                for x in self.octopoes_api_connector.query(
                    "Hostname.<hostname[is Website].certificate.<ooi[is Finding].finding_type",
                    valid_time,
                    web_hostname.reference,
                )
                if x.id in ["KAT-CERTIFICATE-EXPIRED", "KAT-CERTIFICATE-EXPIRING-SOON"]
            ]
            check.certificates_not_expired = check.has_certificates and "KAT-CERTIFICATE-EXPIRED" not in [
                x.id for x in certificate_finding_types
            ]
            check.certificates_not_expiring_soon = check.has_certificates and "KAT-CERTIFICATE-EXPIRING-SOON" in [
                x.id for x in certificate_finding_types
            ]

            web_checks.checks.append(check)

            new_types = (
                csp_finding_types
                + csp_vulnerabilities_finding_types
                + url_finding_types
                + no_certificate_finding_types
                + port_finding_types
                + certificate_finding_types
            )

            for finding_type in new_types:
                if finding_type.risk_severity in [None, RiskLevelSeverity.PENDING] or not finding_type.description:
                    continue

                finding_types[finding_type.id] = finding_type

        return {
            "input_ooi": input_ooi,
            "web_checks": web_checks,
            "finding_types": sorted(finding_types.values(), reverse=True, key=lambda x: x.risk_severity),
        }
