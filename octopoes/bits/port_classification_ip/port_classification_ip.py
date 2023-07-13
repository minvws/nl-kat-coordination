from typing import Dict, Iterator, List

from octopoes.models import OOI
from octopoes.models.ooi.findings import Finding, KATFindingType
from octopoes.models.ooi.network import IPPort, Protocol

COMMON_TCP_PORTS = [
    25,  # SMTP
    53,  # DNS
    80,  # HTTP
    110,  # POP3
    143,  # IMAP
    443,  # HTTPS
    465,  # SMTPS
    587,  # SMTP (message submmission)
    993,  # IMAPS
    995,  # POP3S
]

COMMON_UDP_PORTS = [
    53,  # DNS
]

SA_TCP_PORTS = [
    21,  # FTP
    22,  # SSH
    23,  # Telnet
    3389,  # Remote Desktop
    5900,  # VNC
]
DB_TCP_PORTS = [
    1433,  # MS SQL Server
    1434,  # MS SQL Server
    3050,  # Interbase/Firebase
    3306,  # MySQL
    5432,  # PostgreSQL
]


def run(input_ooi: IPPort, additional_oois: List, config: Dict[str, str]) -> Iterator[OOI]:
    aggregate_findings = config.get("aggregate_findings", "False").lower() == "true" if config else False
    open_ports = []
    for ip_port in additional_oois:
        port = ip_port.port
        protocol = ip_port.protocol
        if protocol == Protocol.TCP and port in SA_TCP_PORTS:
            open_sa_port = KATFindingType(id="KAT-OPEN-SYSADMIN-PORT")
            if aggregate_findings:
                open_ports.append(ip_port.port)
            else:
                yield open_sa_port
                yield Finding(
                    finding_type=open_sa_port.reference,
                    ooi=ip_port.reference,
                    description=f"Port {port}/{protocol.value} is a system administrator port and should not be open.",
                )
        elif protocol == Protocol.TCP and port in DB_TCP_PORTS:
            ft = KATFindingType(id="KAT-OPEN-DATABASE-PORT")
            if aggregate_findings:
                open_ports.append(ip_port.port)
            else:
                yield ft
                yield Finding(
                    finding_type=ft.reference,
                    ooi=ip_port.reference,
                    description=f"Port {port}/{protocol.value} is a database port and should not be open.",
                )
        elif (protocol == Protocol.TCP and port not in COMMON_TCP_PORTS) or (
            protocol == Protocol.UDP and port not in COMMON_UDP_PORTS
        ):
            kat = KATFindingType(id="KAT-UNCOMMON-OPEN-PORT")
            if aggregate_findings:
                open_ports.append(ip_port.port)
            else:
                yield kat
                yield Finding(
                    finding_type=kat.reference,
                    ooi=ip_port.reference,
                    description=f"Port {port}/{protocol.value} is not a common port and should possibly not be open.",
                )
    if aggregate_findings and open_ports:
        ft = KATFindingType(
            id="KAT-UNCOMMON-OPEN-PORT",
        )
        yield ft
        yield Finding(
            finding_type=ft.reference,
            ooi=input_ooi.reference,
            description=f"Ports {', '.join([str(port) for port in open_ports])} are not common ports and should "
            f"possibly not be open.",
        )
