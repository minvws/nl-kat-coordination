from collections.abc import Iterator

from octopoes.models import OOI
from octopoes.models.ooi.dns.zone import ResolvedHostname
from octopoes.models.ooi.network import IPAddress, IPPort, Network
from octopoes.models.ooi.web import URL


def run(
    ip_address: IPAddress, additional_oois: list[IPPort | ResolvedHostname], config: dict[str, str]
) -> Iterator[OOI]:
    hostnames = [resolved.hostname for resolved in additional_oois if isinstance(resolved, ResolvedHostname)]
    ip_ports = [ip_port for ip_port in additional_oois if isinstance(ip_port, IPPort)]

    for ip_port in ip_ports:
        if ip_port.port == 443:
            for hostname in hostnames:
                yield URL(
                    network=Network(name=hostname.tokenized.network.name).reference,
                    raw=f"https://{hostname.tokenized.name}/",
                )
        if ip_port.port == 80:
            for hostname in hostnames:
                yield URL(
                    network=Network(name=hostname.tokenized.network.name).reference,
                    raw=f"http://{hostname.tokenized.name}/",
                )
