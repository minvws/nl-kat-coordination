import logging
from typing import Iterable, Iterator, Union

from libnmap.objects import NmapHost, NmapService
from libnmap.parser import NmapParser

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI, Reference
from octopoes.models.ooi.network import (
    IPAddressV4,
    IPAddressV6,
    IPPort,
    Network,
    PortState,
    Protocol,
)
from octopoes.models.ooi.service import IPService, Service


def get_ip_ports_and_service(host: NmapHost, network: Network, netblock: Reference) -> Iterator[OOI]:
    """Yields IPs, open ports and services if any ports are open on this host."""
    open_ports = host.get_open_ports()
    if open_ports:
        ip = (
            IPAddressV4(network=network.reference, address=host.address, netblock=netblock)
            if host.ipv4
            else IPAddressV6(network=network.reference, address=host.address, netblock=netblock)
        )

        for port, protocol in open_ports:
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
            if service_name == "http" and service.tunnel == "ssl":
                service_name = "https"

            port_service = Service(name=service_name)
            yield port_service

            ip_service = IPService(ip_port=ip_port.reference, service=port_service.reference)
            yield ip_service


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterable[OOI]:
    """Decouple and parse Nmap XMLs and yield relevant network."""
    # Multiple XMLs are concatenated through "\n\n". XMLs end with "\n"; we split on "\n\n\n".
    raw = raw.decode().split("\n\n\n")

    # Relevant network object is received from the normalizer_meta.
    network = Network(name=normalizer_meta.raw_data.boefje_meta.arguments["input"]["network"]["name"])
    yield network

    netblock_ref = None
    if "NetBlock" in normalizer_meta.raw_data.boefje_meta.arguments["input"]["object_type"]:
        netblock_ref = Reference.from_str(normalizer_meta.raw_data.boefje_meta.input_ooi)

    logging.info("Parsing %d Nmap-xml(s) for %s.", len(raw), network)
    for r in raw:
        for host in NmapParser.parse_fromstring(r).hosts:
            yield from get_ip_ports_and_service(host=host, network=network, netblock=netblock_ref)
