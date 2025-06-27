from collections.abc import Iterator

from octopoes.models import OOI
from octopoes.models.ooi.findings import Finding, KATFindingType
from octopoes.models.ooi.network import IPAddress, IPPort
from octopoes.models.ooi.web import Website


def nibble(ipaddress: IPAddress, ipport80: IPPort, website: Website, port443s: int) -> Iterator[OOI]:
    _ = ipaddress
    _ = ipport80
    if port443s < 1:
        ft = KATFindingType(id="KAT-HTTPS-NOT-AVAILABLE")
        yield ft
        yield Finding(
            ooi=website.reference,
            finding_type=ft.reference,
            description="HTTP port is open, but HTTPS port is not open",
        )
