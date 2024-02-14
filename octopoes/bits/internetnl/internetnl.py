from collections.abc import Iterator

from octopoes.models import OOI
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.findings import Finding, KATFindingType
from octopoes.models.ooi.web import Website


def run(input_ooi: Hostname, additional_oois: list[Finding | Website], config: dict[str, str]) -> Iterator[OOI]:
    # only websites have to comply with the internetnl rules
    websites = [websites for websites in additional_oois if isinstance(websites, Website)]
    if not websites:
        return

    finding_ids = [finding.finding_type.tokenized.id for finding in additional_oois if isinstance(finding, Finding)]

    result = ""
    internetnl_findings = {
        "KAT-WEBSERVER-NO-IPV6": "This webserver does not have an IPv6 address",
        "KAT-NAMESERVER-NO-TWO-IPV6": "This webserver does not have at least two nameservers with an IPv6 address",
        "KAT-NO-DNSSEC": "This webserver is not DNSSEC signed",
        "KAT-INVALID-DNSSEC": "The DNSSEC signature of this webserver is not valid",
        "KAT-NO-HSTS": "This website has at least one webpage with a missing Strict-Transport-Policy header",
        "KAT-NO-CSP": "This website has at least one webpage with a missing Content-Security-Policy header",
        "KAT-NO-X-FRAME-OPTIONS": "This website has at least one webpage with a missing X-Frame-Options header",
        "KAT-NO-X-CONTENT-TYPE-OPTIONS": (
            "This website has at least one webpage with a missing X-Content-Type-Options header"
        ),
        "KAT-CSP-VULNERABILITIES": "This website has at least one webpage with a mis-configured CSP header",
        "KAT-HSTS-VULNERABILITIES": "This website has at least one webpage with a mis-configured HSTS header",
        "KAT-NO-CERTIFICATE": "This website does not have an SSL certificate",
        "KAT-HTTPS-NOT-AVAILABLE": "HTTPS is not available for this website",
        "KAT-SSL-CERT-HOSTNAME-MISMATCH": "The SSL certificate of this website does not match the hostname",
        "KAT-HTTPS-REDIRECT": "This website has at least one HTTP URL that does not redirect to HTTPS",
    }

    for finding, description in internetnl_findings.items():
        if finding in finding_ids:
            result += f"{description}\n"

    if result:
        ft = KATFindingType(id="KAT-INTERNETNL")
        yield ft
        f = Finding(
            finding_type=ft.reference,
            ooi=input_ooi.reference,
            description=f"This hostname has at least one website with the following finding(s): {result}",
        )
        yield f
