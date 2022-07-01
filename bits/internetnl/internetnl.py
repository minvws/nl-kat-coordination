from typing import List, Iterator, Union

from octopoes.models import OOI
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.findings import KATFindingType, Finding
from octopoes.models.ooi.web import Website


def run(
    input_ooi: Hostname,
    additional_oois: List[Union[Finding, Website]],
) -> Iterator[OOI]:

    # only websites have to comply with the internetnl rules
    websites = [websites for websites in additional_oois if isinstance(websites, Website)]
    if not websites:
        return

    finding_ids = [finding.finding_type.tokenized.id for finding in additional_oois if isinstance(finding, Finding)]

    result = ""
    internetnl_findings = {
        "KAT-581": "This webserver does not have an IPv6 address",
        "KAT-NAMESERVER-NO-TWO-IPV6": "This webserver does not have at least two nameservers with an IPv6 address",
        "KAT-600": "This webserver is not DNSSEC signed",
        "KAT-601": "The DNSSEC signature of this webserver is not valid",
        "KAT-500": "This website has at least one webpage with a missing Strict-Transport-Policy header",
        "KAT-501": "This website has at least one webpage with a missing Content-Security-Policy header",
        "KAT-504": "This website has at least one webpage with a missing X-Frame-Options header",
        "KAT-509": "This website has at least one webpage with a missing X-Content-Type-Options header",
        "KAT-607": "This website has at least one webpage with a mis-configured CSP header",
        "KAT-606": "This website has at least one webpage with a mis-configured HSTS header",
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
