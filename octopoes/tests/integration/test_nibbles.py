import os
import sys
from collections.abc import Iterator
from datetime import datetime
from ipaddress import IPv4Address, ip_address
from unittest.mock import Mock

import pytest
from nibbles.definitions import NibbleDefinition
from nibbles.runner import NibblesRunner

from octopoes.core.service import OctopoesService
from octopoes.models import OOI, ScanLevel
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.findings import Finding, KATFindingType
from octopoes.models.ooi.network import IPAddressV4, IPAddressV6, Network
from octopoes.models.ooi.web import URL, HostnameHTTPURL, IPAddressHTTPURL, WebScheme

if os.environ.get("CI") != "1":
    pytest.skip("Needs XTDB multinode container.", allow_module_level=True)


MAX_NETWORK_NAME_LENGTH = 13


def dummy(network: Network) -> Network | None:
    if len(network.name) < MAX_NETWORK_NAME_LENGTH:
        new_name = network.name + "I"
        return Network(name=new_name)


dummy_nibble = NibbleDefinition(name="dummy", signature=[Network])
dummy_nibble.payload = getattr(sys.modules[__name__], "dummy")


def test_dummy_nibble(xtdb_octopoes_service: OctopoesService, event_manager: Mock, valid_time: datetime):
    xtdb_octopoes_service.nibbler.nibbles = [dummy_nibble]
    network = Network(name="internet")
    xtdb_octopoes_service.ooi_repository.save(network, valid_time)
    event_manager.complete_process_events(xtdb_octopoes_service)

    assert xtdb_octopoes_service.ooi_repository.list_oois({Network}, valid_time).count == 1
    assert xtdb_octopoes_service.ooi_repository.list_oois({OOI}, valid_time).count == 3

    sp = xtdb_octopoes_service.scan_profile_repository.get(network.reference, valid_time)
    new_sp = sp.model_copy()
    new_sp.level = ScanLevel.L2
    xtdb_octopoes_service.scan_profile_repository.save(sp, new_sp, valid_time)
    event_manager.complete_process_events(xtdb_octopoes_service)

    ctx = 1 + MAX_NETWORK_NAME_LENGTH - len(network.name)
    assert xtdb_octopoes_service.ooi_repository.list_oois({Network}, valid_time).count == ctx
    assert xtdb_octopoes_service.ooi_repository.list_oois({OOI}, valid_time).count == 3 * ctx


def url_classification(url: URL) -> Iterator[OOI]:
    if url.raw.scheme == "http" or url.raw.scheme == "https":
        port = url.raw.port
        if port is None:
            if url.raw.scheme == "https":
                port = 443
            elif url.raw.scheme == "http":
                port = 80

        path = url.raw.path if url.raw.path is not None else "/"

        default_args = {"network": url.network, "scheme": WebScheme(url.raw.scheme), "port": port, "path": path}
        try:
            addr = ip_address(url.raw.host)
        except ValueError:
            hostname = Hostname(network=url.network, name=url.raw.host)
            hostname_url = HostnameHTTPURL(netloc=hostname.reference, **default_args)
            original_url = URL(network=url.network, raw=url.raw, web_url=hostname_url.reference)
            yield hostname
            yield hostname_url
            yield original_url
        else:
            if isinstance(addr, IPv4Address):
                ip = IPAddressV4(network=url.network, address=addr)
                ip_url = IPAddressHTTPURL(netloc=ip.reference, **default_args)
                original_url = URL(network=url.network, raw=url.raw, web_url=ip_url.reference)
                yield ip
                yield ip_url
                yield original_url
            else:
                ip = IPAddressV6(network=url.network, address=addr)
                ip_url = IPAddressHTTPURL(netloc=ip.reference, **default_args)
                original_url = URL(network=url.network, raw=url.raw, web_url=ip_url.reference)
                yield ip
                yield ip_url
                yield original_url


url_classification_nibble = NibbleDefinition(name="url_classification", signature=[URL], min_scan_level=-1)
url_classification_nibble.payload = getattr(sys.modules[__name__], "url_classification")


def test_url_classification_nibble(xtdb_octopoes_service: OctopoesService, event_manager: Mock, valid_time: datetime):
    nibbler = NibblesRunner(
        xtdb_octopoes_service.ooi_repository,
        xtdb_octopoes_service.origin_repository,
        xtdb_octopoes_service.scan_profile_repository,
    )
    nibbler.nibbles = [url_classification_nibble]
    network = Network(name="internet")
    xtdb_octopoes_service.ooi_repository.save(network, valid_time)
    url = URL(network=network.reference, raw="https://mispo.es/")
    xtdb_octopoes_service.ooi_repository.save(url, valid_time)
    event_manager.complete_process_events(xtdb_octopoes_service)

    result = nibbler.infer([url], valid_time)

    assert url in result
    assert "url_classification" in result[url]
    assert len(result[url]["url_classification"]) == 1
    assert len(result[url]["url_classification"][0]) == 2
    assert result[url]["url_classification"][0][0][0] == url
    assert len(result[url]["url_classification"][0][1]) == 3


def find_network_url(network1: Network, network2: Network) -> Iterator[OOI]:
    if len(network1.name) == len(network2.name):
        yield Finding(
            finding_type=KATFindingType(id="Same Network Name Length").reference,
            ooi=network1.reference,
            proof=network2.reference,
        )


find_network_url_nibble = NibbleDefinition(
    name="find_network_url",
    signature=[Network, URL],
    query='{:query {:find [(pull ?var [*])] :where [[?var :object_type "Network"]]}}',
    min_scan_level=-1,
)
find_network_url_nibble.payload = getattr(sys.modules[__name__], "find_network_url")


def test_find_network_url_nibble(xtdb_octopoes_service: OctopoesService, event_manager: Mock, valid_time: datetime):
    nibbler = NibblesRunner(
        xtdb_octopoes_service.ooi_repository,
        xtdb_octopoes_service.origin_repository,
        xtdb_octopoes_service.scan_profile_repository,
    )
    nibbler.nibbles = [find_network_url_nibble]
    network1 = Network(name="internet1")
    xtdb_octopoes_service.ooi_repository.save(network1, valid_time)
    network2 = Network(name="internet2")
    xtdb_octopoes_service.ooi_repository.save(network2, valid_time)
    event_manager.complete_process_events(xtdb_octopoes_service)

    with pytest.raises(NotImplementedError):
        nibbler.infer([network1], valid_time)
