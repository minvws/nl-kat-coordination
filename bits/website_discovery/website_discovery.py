from typing import List, Iterator, Union

from octopoes.models import OOI
from octopoes.models.ooi.dns.zone import ResolvedHostname
from octopoes.models.ooi.network import IPAddressV4
from octopoes.models.ooi.service import IPService
from octopoes.models.ooi.web import Website


def run(
    ip_address: IPAddressV4,
    additional_oois: List[Union[IPService, ResolvedHostname]],
) -> Iterator[OOI]:
    def is_service_http(ip_service: IPService) -> bool:
        return "http" in ip_service.service.tokenized.name.lower().strip()

    hostnames = [resolved.hostname for resolved in additional_oois if isinstance(resolved, ResolvedHostname)]
    services = [ip_service for ip_service in additional_oois if isinstance(ip_service, IPService)]
    http_services = filter(is_service_http, services)

    # website is cartesian product of hostname and http services
    for http_service in http_services:
        for hostname in hostnames:
            yield Website(
                hostname=hostname,
                ip_service=http_service.reference,
            )
