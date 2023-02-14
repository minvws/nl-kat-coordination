from typing import List, Iterator

from octopoes.models import OOI
from octopoes.models.ooi.findings import KATFindingType, Finding
from octopoes.models.ooi.network import IPPort

COMMON_TCP_PORTS = [25, 53, 110, 143, 993, 995, 80, 443]
SA_PORTS = [21, 22, 23, 3389, 5900]
DB_PORTS = [1433, 1434, 3050, 3306, 5432]


def run(
    input_ooi: IPPort,
    additional_oois: List,
) -> Iterator[OOI]:

    port = input_ooi.port
    if port in SA_PORTS:
        open_sa_port = KATFindingType(id="KAT-560")
        yield open_sa_port
        yield Finding(
            finding_type=open_sa_port.reference,
            ooi=input_ooi.reference,
            description=f"Port {port} is a system administrator port and should not be open.",
        )

    if port in DB_PORTS:
        ft = KATFindingType(id="KAT-561")
        yield ft
        yield Finding(
            finding_type=ft.reference,
            ooi=input_ooi.reference,
            description=f"Port {port} is a database port and should not be open.",
        )

    if port not in COMMON_TCP_PORTS and port not in SA_PORTS and port not in DB_PORTS:
        kat = KATFindingType(id="KAT-562")
        yield kat
        yield Finding(
            finding_type=kat.reference,
            ooi=input_ooi.reference,
            description=f"Port {port} is not a common port and should possibly not be open.",
        )
