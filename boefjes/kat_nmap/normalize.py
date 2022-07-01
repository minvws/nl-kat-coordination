from typing import Iterator, Union

from libnmap.objects import NmapHost, NmapService, NmapReport
from libnmap.parser import NmapParser
from octopoes.models import OOI
from octopoes.models.ooi.network import (
    IPAddressV6,
    IPPort,
    Network,
    IPAddressV4,
    Protocol,
    PortState,
)
from octopoes.models.ooi.service import Service, IPService

from job import NormalizerMeta


def get_ports_and_service(host: NmapHost) -> Iterator[OOI]:
    internet = Network(name="internet")
    yield internet

    ip = (
        IPAddressV4(network=internet.reference, address=host.address)
        if host.ipv4
        else IPAddressV6(network=internet.reference, address=host.address)
    )
    yield ip

    for port, protocol in host.get_open_ports():
        service: NmapService = host.get_service(port, protocol)

        # If service is tcpwrapped we should consider the port closed
        if service.service == "tcpwrapped":
            continue

        ip_port = IPPort(
            address=ip.reference,
            protocol=Protocol(protocol),
            port=port,
            state=PortState(service.state),
        )
        yield ip_port

        service_name = service.service
        if port == 80:
            service_name = "http"
        if port == 443:
            service_name = "https"

        port_service = Service(name=service_name)
        yield port_service

        ip_service = IPService(
            ip_port=ip_port.reference, service=port_service.reference
        )
        yield ip_service


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterator[OOI]:

    parsed: NmapReport = NmapParser.parse_fromstring(raw.decode())

    for host in parsed.hosts:
        yield from get_ports_and_service(host)
