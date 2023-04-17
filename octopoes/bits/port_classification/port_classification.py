from typing import Iterator, List, Union

from octopoes.models import OOI
from octopoes.models.ooi.findings import Finding, KATFindingType
from octopoes.models.ooi.network import IPPort, Protocol

COMMON_TCP_PORTS = [25, 53, 110, 143, 993, 995, 80, 443]
SA_PORTS = [21, 22, 23, 3389, 5900]
DB_PORTS = [1433, 1434, 3050, 3306, 5432]


def yield_port(ooi_reference, finding_id: str, finding_description: str) -> Union[KATFindingType, Finding]:
    """Yields a finding for a specific port."""
    finding_type = KATFindingType(id=finding_id)
    yield finding_type
    yield Finding(finding_type=finding_type.reference, ooi=ooi_reference, description=finding_description)


def run(
    input_ooi: IPPort,
    additional_oois: List,
) -> Iterator[OOI]:
    """Decides port type and returns finding accordingly."""
    port = input_ooi.port
    if port in SA_PORTS:
        finding_id = "KAT-OPEN-SYSADMIN-PORT"
        port_type = "a system administrator"
    elif port in DB_PORTS:
        finding_id = "KAT-OPEN-DATABASE-PORT"
        port_type = "a database"
    elif port in COMMON_TCP_PORTS and input_ooi.protocol == Protocol.TCP:
        finding_id = "KAT-OPEN-COMMON-TCP-PORT"
        port_type = "a common TCP"
    else:
        finding_id = "KAT-UNCOMMON-OPEN-PORT"
        port_type = "not a common"

    yield from yield_port(
        ooi_reference=input_ooi.reference,
        finding_id=finding_id,
        finding_description=f"Port {port} is usually {port_type} port and found to be open.",
    )
