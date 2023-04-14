from typing import List, Iterator

from octopoes.models import OOI
from octopoes.models.ooi.findings import KATFindingType, Finding
from octopoes.models.ooi.network import IPPort

COMMON_TCP_PORTS = [25, 53, 110, 143, 993, 995, 80, 443]


def run(
    input_ooi: IPPort,
    additional_oois: List,
) -> Iterator[OOI]:
    port = input_ooi.port
    if port in COMMON_TCP_PORTS:
        kat = KATFindingType(id="KAT-OPEN-COMMON-PORT")
        yield kat
        yield Finding(
            finding_type=kat.reference,
            ooi=input_ooi.reference,
            description=f"Port {port} is a common port and found to be open.",
        )
