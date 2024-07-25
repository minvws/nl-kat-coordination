from collections.abc import Iterator

from octopoes.models import OOI
from octopoes.models.ooi.dns.records import DNSNSRecord
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.findings import Finding, KATFindingType

INDICATORS = [
    "DNS1.NAME-SERVICES.COM",
    "DNS2.NAME-SERVICES.COM",
    "DNS3.NAME-SERVICES.COM",
    "DNS4.NAME-SERVICES.COM",
    "DNS5.NAME-SERVICES.COM",
    "NS1.REGISTRANT-VERIFICATION.ISPAPI.NET",
    "NS2.REGISTRANT-VERIFICATION.ISPAPI.NET",
    "NS3.REGISTRANT-VERIFICATION.ISPAPI.NET",
]


def run(nameserver: DNSNSRecord, additional_oois: list[Hostname], config: dict[str, str]) -> Iterator[OOI]:
    """Checks to see if a domain has a specific set of dns servers which would indicate domain registrant verification.
    https://support.dnsimple.com/articles/icann-domain-validation/
    """
    if DNSNSRecord.name_server_hostname.rstrip('.').upper() in INDICATORS:
        for hostname in additional_oois:
            finding_type = KATFindingType(id="KAT-DOMAIN-OWNERSHIP-PENDING")
            yield finding_type
            yield Finding(
                finding_type=finding_type.reference,
                ooi=hostname.reference,
                description="This domain requires ownership verification and is currently pending.",
            )
