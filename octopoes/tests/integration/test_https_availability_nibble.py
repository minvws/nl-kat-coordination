import os
from datetime import datetime
from itertools import permutations
from unittest.mock import Mock

import pytest
from nibbles.https_availability.nibble import NIBBLE as https_availability

from octopoes.core.service import OctopoesService
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.findings import Finding, KATFindingType
from octopoes.models.ooi.network import IPAddressV4, IPPort, Network, Protocol
from octopoes.models.ooi.service import IPService, Service
from octopoes.models.ooi.web import HostnameHTTPURL, HTTPHeader, HTTPResource, WebScheme, Website
from octopoes.repositories.ooi_repository import XTDBOOIRepository

if os.environ.get("CI") != "1":
    pytest.skip("Needs XTDB multinode container.", allow_module_level=True)

STATIC_IP = ".".join(4 * ["1"])


def create_port(xtdb_ooi_repository: XTDBOOIRepository, ip: str, port: int, valid_time: datetime) -> IPAddressV4:
    network = Network(name="internet")
    ip = IPAddressV4(address=ip, network=network.reference)
    port = IPPort(port=port, address=ip.reference, protocol=Protocol.TCP)
    hostname = Hostname(name="example.com", network=network.reference)
    service = Service(name="http")
    ip_service = IPService(ip_port=port.reference, service=service.reference)
    website = Website(ip_service=ip_service.reference, hostname=hostname.reference)

    xtdb_ooi_repository.save(network, valid_time)
    xtdb_ooi_repository.save(port, valid_time)
    xtdb_ooi_repository.save(ip, valid_time)
    xtdb_ooi_repository.save(service, valid_time)
    xtdb_ooi_repository.save(ip_service, valid_time)
    xtdb_ooi_repository.save(hostname, valid_time)
    xtdb_ooi_repository.save(website, valid_time)

    xtdb_ooi_repository.commit()

    return ip


def ip_generator():
    for ip in permutations(range(1, 256), 4):
        yield ".".join([str(x) for x in ip])


def test_https_availability_query(xtdb_ooi_repository: XTDBOOIRepository, event_manager: Mock, valid_time: datetime):
    query = https_availability.query([None] * 4)
    ip = ip_generator()

    first_ip = create_port(xtdb_ooi_repository, next(ip), 80, valid_time)
    assert xtdb_ooi_repository.session.client.query(query)[0][-1] == 0

    for _ in range(20):
        create_port(xtdb_ooi_repository, next(ip), 80, valid_time)
    assert xtdb_ooi_repository.session.client.query(query)[0][-1] == 0

    create_port(xtdb_ooi_repository, str(first_ip.address), 443, valid_time)
    assert xtdb_ooi_repository.session.client.query(query)[0][-1] == 1

    for _ in range(12):
        create_port(xtdb_ooi_repository, next(ip), 443, valid_time)
    assert xtdb_ooi_repository.session.client.query(query)[0][-1] == 13


def test_https_availability(xtdb_octopoes_service: OctopoesService, event_manager: Mock, valid_time: datetime):
    xtdb_octopoes_service.nibbler.nibbles = {https_availability.id: https_availability}

    network = Network(name="internet")
    xtdb_octopoes_service.ooi_repository.save(network, valid_time)

    hostname = Hostname(name="example.com", network=network.reference)
    xtdb_octopoes_service.ooi_repository.save(hostname, valid_time)

    web_url = HostnameHTTPURL(
        network=network.reference, netloc=hostname.reference, port=443, path="/", scheme=WebScheme.HTTP
    )
    xtdb_octopoes_service.ooi_repository.save(web_url, valid_time)

    service = Service(name="https")
    xtdb_octopoes_service.ooi_repository.save(service, valid_time)

    ip_address = IPAddressV4(address=STATIC_IP, network=network.reference)
    xtdb_octopoes_service.ooi_repository.save(ip_address, valid_time)

    port = IPPort(port=80, address=ip_address.reference, protocol=Protocol.TCP)
    xtdb_octopoes_service.ooi_repository.save(port, valid_time)

    ip_service = IPService(ip_port=port.reference, service=service.reference)
    xtdb_octopoes_service.ooi_repository.save(ip_service, valid_time)

    website = Website(ip_service=ip_service.reference, hostname=hostname.reference)
    xtdb_octopoes_service.ooi_repository.save(website, valid_time)

    resource = HTTPResource(website=website.reference, web_url=web_url.reference)
    xtdb_octopoes_service.ooi_repository.save(resource, valid_time)

    header = HTTPHeader(
        resource=resource.reference, key="strict-transport-security", value="max-age=21536000; includeSubDomains"
    )
    xtdb_octopoes_service.ooi_repository.save(header, valid_time)

    event_manager.complete_process_events(xtdb_octopoes_service)

    assert xtdb_octopoes_service.ooi_repository.list_oois({Finding}, valid_time).count == 1
    assert (
        xtdb_octopoes_service.ooi_repository.list_oois({Finding}, valid_time).items[0].description
        == "HTTP port is open, but HTTPS port is not open"
    )
    assert xtdb_octopoes_service.ooi_repository.list_oois({KATFindingType}, valid_time).count == 1
    assert (
        xtdb_octopoes_service.ooi_repository.list_oois({KATFindingType}, valid_time).items[0].id
        == "KAT-HTTPS-NOT-AVAILABLE"
    )

    port443 = IPPort(port=443, address=ip_address.reference, protocol=Protocol.TCP)
    xtdb_octopoes_service.ooi_repository.save(port443, valid_time)
    event_manager.complete_process_events(xtdb_octopoes_service)

    assert xtdb_octopoes_service.ooi_repository.list_oois({Finding}, valid_time).count == 0
    assert xtdb_octopoes_service.ooi_repository.list_oois({KATFindingType}, valid_time).count == 0
