from collections.abc import Iterator

from octopoes.models import OOI
from octopoes.models.ooi.findings import Finding, KATFindingType
from octopoes.models.ooi.network import IPAddress, IPPort
from octopoes.models.ooi.web import Website


def run(input_ooi: IPAddress, additional_oois: list[IPPort | Website], config: dict[str, str]) -> Iterator[OOI]:
    websites = [website for website in additional_oois if isinstance(website, Website)]

    open_ports = [port.port for port in additional_oois if isinstance(port, IPPort)]
    if 80 in open_ports and 443 not in open_ports:
        ft = KATFindingType(id="KAT-HTTPS-NOT-AVAILABLE")
        for website in websites:
            yield Finding(
                ooi=website.reference,
                finding_type=ft.reference,
                description="HTTP port is open, but HTTPS port is not open",
            )
