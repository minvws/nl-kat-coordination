import ipaddress
import json
import logging
from typing import Iterable, Iterator, Union

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


def get_ip_ports_and_service(ip_with_ports: dict, network: Network, netblock: Reference) -> Iterator[OOI]:
    """Yields IPs and open ports for any ports open on this host."""
    if "ip" not in ip_with_ports:
        raise ValueError("[Masscan] No IP given in output.")
    if "ports" not in ip_with_ports:
        raise ValueError("[Masscan] No ports argument in IP with ports list.")
    host_ip = ip_with_ports["ip"]
    ip_version = ipaddress.ip_interface(host_ip).ip.version
    ip = (
        IPAddressV4(network=network.reference, address=host_ip, netblock=netblock)
        if ip_version == 4
        else IPAddressV6(network=network.reference, address=host_ip, netblock=netblock)
    )
    yield ip

    for port_dict in ip_with_ports["ports"]:
        ip_port = IPPort(
            address=ip.reference,
            protocol=Protocol(port_dict["proto"]),
            port=port_dict["port"],
            state=PortState(port_dict["status"]),
        )
        yield ip_port


def run(normalizer_meta: NormalizerMeta, raw: Union[bytes, str]) -> Iterable[OOI]:
    """Parse Masscan JSON and yield relevant network, IPs and ports."""
    try:
        raw = json.loads(raw) if raw else []
    except json.decoder.JSONDecodeError:
        # Masscan tends to forget to close the json with "]" if the wait window passed.
        raw = json.loads(raw.decode() + "]") if raw else []

    # Relevant network object is received from the normalizer_meta.
    network = Network(name=normalizer_meta.raw_data.boefje_meta.arguments["input"]["network"]["name"])

    netblock_ref = Reference.from_str(normalizer_meta.raw_data.boefje_meta.input_ooi)

    logging.info("Parsing %d Masscan IPs for %s.", len(raw), network)
    for ip_with_ports in raw:
        yield from get_ip_ports_and_service(ip_with_ports=ip_with_ports, network=network, netblock=netblock_ref)
