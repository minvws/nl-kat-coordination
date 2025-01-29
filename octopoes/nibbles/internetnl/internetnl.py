from collections.abc import Iterator

from octopoes.models import OOI
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.findings import Finding, KATFindingType


def nibble(hostname: Hostname, findings: list[Finding]) -> Iterator[OOI]:
    result = "\n".join([str(finding.description) for finding in findings])

    if result:
        ft = KATFindingType(id="KAT-INTERNETNL")
        yield ft
        yield Finding(
            finding_type=ft.reference,
            ooi=hostname.reference,
            description=f"This hostname has at least one website with the following finding(s): {result}",
        )
