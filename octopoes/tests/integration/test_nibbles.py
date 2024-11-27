import os
import sys
from collections.abc import Iterator
from datetime import datetime
from ipaddress import IPv4Address, ip_address
from unittest.mock import Mock

import pytest
from nibbles.definitions import NibbleDefinition, NibbleParameter
from nibbles.runner import NibblesRunner, nibble_hasher

from octopoes.core.service import OctopoesService
from octopoes.models import OOI, ScanLevel
from octopoes.models.ooi.config import Config
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.findings import Finding, KATFindingType
from octopoes.models.ooi.network import IPAddressV4, IPAddressV6, Network
from octopoes.models.ooi.web import URL, HostnameHTTPURL, IPAddressHTTPURL, WebScheme
from octopoes.models.origin import OriginType

if os.environ.get("CI") != "1":
    pytest.skip("Needs XTDB multinode container.", allow_module_level=True)


MAX_NETWORK_NAME_LENGTH = 13


def dummy(network: Network) -> Network | None:
    if len(network.name) < MAX_NETWORK_NAME_LENGTH:
        new_name = network.name + "I"
        return Network(name=new_name)


dummy_params = [NibbleParameter(object_type=Network)]
dummy_nibble = NibbleDefinition(name="dummy", signature=dummy_params)
dummy_nibble.payload = getattr(sys.modules[__name__], "dummy")


def test_dummy_nibble(xtdb_octopoes_service: OctopoesService, event_manager: Mock, valid_time: datetime):
    xtdb_octopoes_service.nibbler.nibbles = {dummy_nibble.id: dummy_nibble}
    network = Network(name="internet")
    xtdb_octopoes_service.ooi_repository.save(network, valid_time)
    event_manager.complete_process_events(xtdb_octopoes_service)

    assert xtdb_octopoes_service.ooi_repository.list_oois({Network}, valid_time).count == 1
    assert xtdb_octopoes_service.ooi_repository.list_oois({OOI}, valid_time).count == 4

    sp = xtdb_octopoes_service.scan_profile_repository.get(network.reference, valid_time)
    new_sp = sp.model_copy()
    new_sp.level = ScanLevel.L2
    xtdb_octopoes_service.scan_profile_repository.save(sp, new_sp, valid_time)
    event_manager.complete_process_events(xtdb_octopoes_service)

    ctx = 1 + MAX_NETWORK_NAME_LENGTH - len(network.name)
    assert xtdb_octopoes_service.ooi_repository.list_oois({Network}, valid_time).count == ctx
    assert xtdb_octopoes_service.ooi_repository.list_oois({OOI}, valid_time).count == 4 * ctx


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


url_classification_params = [NibbleParameter(object_type=URL)]
url_classification_nibble = NibbleDefinition(
    name="url_classification", signature=url_classification_params, min_scan_level=-1
)
url_classification_nibble.payload = getattr(sys.modules[__name__], "url_classification")


def test_url_classification_nibble(xtdb_octopoes_service: OctopoesService, event_manager: Mock, valid_time: datetime):
    nibbler = NibblesRunner(
        xtdb_octopoes_service.ooi_repository,
        xtdb_octopoes_service.origin_repository,
        xtdb_octopoes_service.scan_profile_repository,
        perform_writes=False,
    )
    nibbler.nibbles = {url_classification_nibble.id: url_classification_nibble}
    network = Network(name="internet")
    xtdb_octopoes_service.ooi_repository.save(network, valid_time)
    url = URL(network=network.reference, raw="https://mispo.es/")
    xtdb_octopoes_service.ooi_repository.save(url, valid_time)
    event_manager.complete_process_events(xtdb_octopoes_service)

    result = nibbler.infer([url], valid_time)

    assert url in result
    assert "url_classification" in result[url]
    assert len(result[url]["url_classification"]) == 1
    assert len(result[url]["url_classification"][tuple([url])]) == 3


def find_network_url(network: Network, url: URL) -> Iterator[OOI]:
    if len(network.name) == len(str(url.raw)):
        yield Finding(
            finding_type=KATFindingType(id="Network and URL have same name length").reference,
            ooi=network.reference,
            proof=url.reference,
        )


find_network_url_params = [
    NibbleParameter(object_type=Network, parser="[*][?object_type == 'Network'][]"),
    NibbleParameter(object_type=URL, parser="[*][?object_type == 'URL'][]"),
]
find_network_url_nibble = NibbleDefinition(
    name="find_network_url",
    signature=find_network_url_params,
    query="""
    {
        :query {
            :find [(pull ?var [*])]
            :where [
                (or
                    (and [?var :object_type "URL" ] [?var :URL/raw])
                    (and [?var :object_type "Network" ] [?var :Network/name])
                )
            ]
        }
    }
    """,
    min_scan_level=-1,
)
find_network_url_nibble.payload = getattr(sys.modules[__name__], "find_network_url")


def test_find_network_url_nibble(xtdb_octopoes_service: OctopoesService, event_manager: Mock, valid_time: datetime):
    nibbler = NibblesRunner(
        xtdb_octopoes_service.ooi_repository,
        xtdb_octopoes_service.origin_repository,
        xtdb_octopoes_service.scan_profile_repository,
    )
    nibbler.nibbles = {find_network_url_nibble.id: find_network_url_nibble}
    network1 = Network(name="internetverbinding")
    xtdb_octopoes_service.ooi_repository.save(network1, valid_time)
    event_manager.complete_process_events(xtdb_octopoes_service)
    network2 = Network(name="internet")
    xtdb_octopoes_service.ooi_repository.save(network2, valid_time)
    event_manager.complete_process_events(xtdb_octopoes_service)
    url1 = URL(network=network1.reference, raw="https://potato.ls/")
    xtdb_octopoes_service.ooi_repository.save(url1, valid_time)
    event_manager.complete_process_events(xtdb_octopoes_service)
    url2 = URL(network=network2.reference, raw="https://mispo.es/")
    xtdb_octopoes_service.ooi_repository.save(url2, valid_time)
    event_manager.complete_process_events(xtdb_octopoes_service)

    xtdb_url1 = xtdb_octopoes_service.ooi_repository.get(url1.reference, valid_time)
    xtdb_url2 = xtdb_octopoes_service.ooi_repository.get(url2.reference, valid_time)

    result = nibbler.infer([network1], valid_time)
    event_manager.complete_process_events(xtdb_octopoes_service)

    target = set(find_network_url(network1, url1))

    assert network1 in result
    assert len(result[network1]["find_network_url"]) == 4
    assert result[network1]["find_network_url"][tuple([network1, xtdb_url1])] == target
    assert result[network1]["find_network_url"][tuple([network2, xtdb_url1])] == set()
    assert result[network1]["find_network_url"][tuple([network1, xtdb_url2])] == set()
    assert result[network1]["find_network_url"][tuple([network2, xtdb_url2])] == set()

    nibblets = xtdb_octopoes_service.origin_repository.list_origins(
        origin_type=OriginType.NIBBLET, valid_time=valid_time
    )

    assert len(nibblets) == 4
    for nibblet in nibblets:
        assert nibblet.parameters_references is not None
        arg = [xtdb_octopoes_service.ooi_repository.get(obj, valid_time) for obj in nibblet.parameters_references]
        assert nibblet.parameters_hash == nibble_hasher(tuple(arg))
        if nibblet.result:
            assert len(nibblet.result) == 1
            assert nibblet.result == [t.reference for t in target]


def max_url_length_config(url: URL, config: Config) -> Iterator[OOI]:
    if "max_length" in config.config:
        max_length = int(str(config.config["max_length"]))
        if len(str(url.raw)) >= max_length:
            yield Finding(
                finding_type=KATFindingType(id="URL exceeds configured maximum length").reference,
                ooi=url.reference,
                proof=f"The length of {url.raw} ({len(str(url.raw))}) exceeds the configured maximum length \
                ({max_length}).",
            )


max_url_length_config_params = [
    NibbleParameter(object_type=URL, parser="[*][?object_type == 'URL'][]"),
    NibbleParameter(object_type=Config, parser="[*][?object_type == 'Config'][]"),
]
max_url_length_config_nibble = NibbleDefinition(
    name="max_url_length_config",
    signature=max_url_length_config_params,
    query="""
    {
        :query {
            :find [(pull ?var [*])]
            :where [
                (or
                    (and [?var :object_type "URL" ] [?var :URL/primary_key $1])
                    (and [?var :object_type "Config" ] [?var :Config/primary_key $2])
                )
            ]
        }
    }
    """,
    min_scan_level=-1,
)
max_url_length_config_nibble.payload = getattr(sys.modules[__name__], "max_url_length_config")


def test_max_length_config_nibble(xtdb_octopoes_service: OctopoesService, event_manager: Mock, valid_time: datetime):
    nibbler = NibblesRunner(
        xtdb_octopoes_service.ooi_repository,
        xtdb_octopoes_service.origin_repository,
        xtdb_octopoes_service.scan_profile_repository,
    )
    nibbler.nibbles = {max_url_length_config_nibble.id: max_url_length_config_nibble}
    network = Network(name="internet")
    xtdb_octopoes_service.ooi_repository.save(network, valid_time)
    url = URL(network=network.reference, raw="https://mispo.es/")
    xtdb_octopoes_service.ooi_repository.save(url, valid_time)
    config = Config(ooi=network.reference, bit_id="superkat", config={"max_length": "57"})
    xtdb_octopoes_service.ooi_repository.save(config, valid_time)
    event_manager.complete_process_events(xtdb_octopoes_service)

    result = nibbler.infer([url], valid_time)
    event_manager.complete_process_events(xtdb_octopoes_service)

    assert url in result
    # FIXME: wait shouldn't this be one?
    assert len(result[url]["max_url_length_config"]) == 2
    assert result[url]["max_url_length_config"][tuple([url, config])] == set()

    config = Config(ooi=network.reference, bit_id="superkat", config={"max_length": "13"})
    xtdb_octopoes_service.ooi_repository.save(config, valid_time)
    event_manager.complete_process_events(xtdb_octopoes_service)

    result = nibbler.infer([url], valid_time)
    event_manager.complete_process_events(xtdb_octopoes_service)

    assert url in result
    # FIXME: wait shouldn't this be one?
    assert len(result[url]["max_url_length_config"]) == 2
    assert result[url]["max_url_length_config"][tuple([url, config])] == set(max_url_length_config(url, config))
