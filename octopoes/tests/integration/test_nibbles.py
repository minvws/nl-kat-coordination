import os
import sys
from collections.abc import Iterator
from datetime import datetime
from unittest.mock import Mock

import pytest
from nibbles.definitions import NibbleDefinition, NibbleParameter
from nibbles.runner import NibblesRunner, nibble_hasher

from octopoes.core.service import OctopoesService
from octopoes.events.events import OOIDBEvent, OperationType, OriginDBEvent
from octopoes.models import OOI, Reference
from octopoes.models.ooi.config import Config
from octopoes.models.ooi.findings import Finding, FindingType, KATFindingType, RiskLevelSeverity
from octopoes.models.ooi.network import Network
from octopoes.models.ooi.web import URL
from octopoes.models.origin import OriginType

if os.environ.get("CI") != "1":
    pytest.skip("Needs XTDB multinode container.", allow_module_level=True)


MAX_NETWORK_NAME_LENGTH = 13


def dummy(network: Network) -> Network | None:
    if len(network.name) < MAX_NETWORK_NAME_LENGTH:
        new_name = network.name + "I"
        return Network(name=new_name)


dummy_params = [NibbleParameter(object_type=Network)]
dummy_nibble = NibbleDefinition(id="dummy", signature=dummy_params)
dummy_nibble._payload = getattr(sys.modules[__name__], "dummy")


def test_dummy_nibble(xtdb_octopoes_service: OctopoesService, event_manager: Mock, valid_time: datetime):
    xtdb_octopoes_service.nibbler.nibbles = {dummy_nibble.id: dummy_nibble}
    network = Network(name="internet")
    xtdb_octopoes_service.ooi_repository.save(network, valid_time)
    event_manager.complete_process_events(xtdb_octopoes_service)

    ctx = 1 + MAX_NETWORK_NAME_LENGTH - len(network.name)
    assert xtdb_octopoes_service.ooi_repository.list_oois({Network}, valid_time).count == ctx
    assert xtdb_octopoes_service.ooi_repository.list_oois({OOI}, valid_time).count == ctx


def test_url_classification_nibble(xtdb_octopoes_service: OctopoesService, event_manager: Mock, valid_time: datetime):
    nibbler = NibblesRunner(
        xtdb_octopoes_service.ooi_repository,
        xtdb_octopoes_service.origin_repository,
        xtdb_octopoes_service.nibbler.nibble_repository,
    )
    nibble = xtdb_octopoes_service.nibbler.nibbles["url_classification"]
    xtdb_octopoes_service.nibbler.disable()
    nibbler.nibbles = {nibble.id: nibble}
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
    id="find_network_url",
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
)
find_network_url_nibble._payload = getattr(sys.modules[__name__], "find_network_url")


def test_find_network_url_nibble(xtdb_octopoes_service: OctopoesService, event_manager: Mock, valid_time: datetime):
    nibbler = NibblesRunner(
        xtdb_octopoes_service.ooi_repository,
        xtdb_octopoes_service.origin_repository,
        xtdb_octopoes_service.nibbler.nibble_repository,
    )
    xtdb_octopoes_service.nibbler.disable()
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
        arg = [
            xtdb_octopoes_service.ooi_repository.get(obj, valid_time)
            for obj in nibblet.parameters_references
            if obj is not None
        ]
        assert nibblet.parameters_hash == nibble_hasher(tuple(arg))
        if nibblet.result:
            assert len(nibblet.result) == 1
            assert nibblet.result == [t.reference for t in target]


def test_max_length_config_nibble(xtdb_octopoes_service: OctopoesService, event_manager: Mock, valid_time: datetime):
    nibbler = NibblesRunner(
        xtdb_octopoes_service.ooi_repository,
        xtdb_octopoes_service.origin_repository,
        xtdb_octopoes_service.nibbler.nibble_repository,
    )
    nibble = xtdb_octopoes_service.nibbler.nibbles["max_url_length_config"]
    nibbler.nibbles = {"max_url_length_config": nibble}
    xtdb_octopoes_service.nibbler.disable()
    network = Network(name="internet")
    xtdb_octopoes_service.ooi_repository.save(network, valid_time)
    url = URL(network=network.reference, raw="https://mispo.es/")
    xtdb_octopoes_service.ooi_repository.save(url, valid_time)
    config = Config(ooi=network.reference, bit_id="superkat", config={"max_length": "57"})
    xtdb_octopoes_service.ooi_repository.save(config, valid_time)
    event_manager.complete_process_events(xtdb_octopoes_service)

    xtdb_url = xtdb_octopoes_service.ooi_repository.get(url.reference, valid_time)

    result = nibbler.infer([xtdb_url], valid_time)
    event_manager.complete_process_events(xtdb_octopoes_service)

    assert xtdb_url in result
    assert len(result[xtdb_url]["max_url_length_config"]) == 1
    assert result[xtdb_url]["max_url_length_config"][tuple([xtdb_url, config])] == set()

    config = Config(ooi=network.reference, bit_id="superkat", config={"max_length": "13"})
    xtdb_octopoes_service.ooi_repository.save(config, valid_time)
    event_manager.complete_process_events(xtdb_octopoes_service)

    result = nibbler.infer([xtdb_url], valid_time)
    event_manager.complete_process_events(xtdb_octopoes_service)

    assert xtdb_url in result
    assert len(result[xtdb_url]["max_url_length_config"]) == 1
    assert result[xtdb_url]["max_url_length_config"][tuple([xtdb_url, config])] == set(nibble([xtdb_url, config]))


def callable_query(url1: URL, url2: URL) -> Iterator[OOI]:
    if url1.raw == url2.raw and url1.network != url2.network:
        yield Finding(
            finding_type=KATFindingType(id="Duplicate URL's under different network").reference,
            ooi=url1.reference,
            proof=f"{url1.reference} matches {url2.reference}.",
        )


callable_query_param = [
    NibbleParameter(object_type=URL, parser='[*].{"URL1": @[1]}[?"URL1"] | [?URL1.object_type == \'URL\'].URL1'),
    NibbleParameter(object_type=URL, parser='[*].{"URL2": @[3]}[?"URL2"] | [?URL2.object_type == \'URL\'].URL2'),
]


def callable_query_query(targets: list[Reference | None]) -> str:
    sgn = "".join(str(int(isinstance(target, Reference))) for target in targets)
    if sgn == "10":
        return f"""{{
                :query {{
                    :find ["URL1" (pull ?url1 [*]) "URL2" (pull ?url2 [*])]
                    :where [
                        [?url1 :URL/primary_key "{str(targets[0])}"]
                        [?url2 :object_type "URL"]
                    ]
                  }}
                }}
                """
    else:
        return f"""{{
                :query {{
                    :find ["URL1" (pull ?url1 [*]) "URL2" (pull ?url2 [*])]
                    :where [
                        [?url1 :URL/primary_key "{str(targets[0])}"]
                        [?url2 :URL/primary_key "{str(targets[1])}"]
                    ]
                  }}
                }}
                """


callable_query_nibble = NibbleDefinition(
    id="callable_nibble_query", signature=callable_query_param, query=callable_query_query
)
callable_query_nibble._payload = getattr(sys.modules[__name__], "callable_query")


def test_callable_query(xtdb_octopoes_service: OctopoesService, event_manager: Mock, valid_time: datetime):
    xtdb_octopoes_service.nibbler.nibbles = {"callable_nibble_query": callable_query_nibble}
    network1 = Network(name="internet1")
    network2 = Network(name="internet2")

    xtdb_octopoes_service.ooi_repository.save(network1, valid_time)
    xtdb_octopoes_service.ooi_repository.save(network2, valid_time)

    event_manager.complete_process_events(xtdb_octopoes_service)

    for url in ["https://mispo.es", "https://appelmo.es", "https://boesbo.es"]:
        xtdb_octopoes_service.ooi_repository.save(URL(network=network1.reference, raw=url), valid_time)

    for url in ["https://tompo.es", "https://smo.es", "https://mispo.es"]:
        xtdb_octopoes_service.ooi_repository.save(URL(network=network2.reference, raw=url), valid_time)

    event_manager.complete_process_events(xtdb_octopoes_service)

    url1 = URL(network=network1.reference, raw="https://mispo.es").reference
    url2 = URL(network=network2.reference, raw="https://mispo.es").reference
    xtdb_url1 = xtdb_octopoes_service.ooi_repository.get(url1, valid_time)
    xtdb_url2 = xtdb_octopoes_service.ooi_repository.get(url2, valid_time)
    finding = list(callable_query(xtdb_url1, xtdb_url2))

    result = xtdb_octopoes_service.ooi_repository.list_oois({Finding}, valid_time)
    assert result.count == 2
    assert finding[0] in result.items


mock_finding_type_nibble = NibbleDefinition(
    id="default-findingtype-risk", signature=[NibbleParameter(object_type=FindingType)]
)


def set_default_severity(input_ooi: FindingType) -> Iterator[OOI]:
    input_ooi.risk_severity = RiskLevelSeverity.PENDING
    yield input_ooi


mock_finding_type_nibble._payload = getattr(sys.modules[__name__], "set_default_severity")


def test_parent_type_in_nibble_signature(
    xtdb_octopoes_service: OctopoesService, event_manager: Mock, valid_time: datetime
):
    nibbler = NibblesRunner(
        xtdb_octopoes_service.ooi_repository,
        xtdb_octopoes_service.origin_repository,
        xtdb_octopoes_service.nibbler.nibble_repository,
    )
    xtdb_octopoes_service.nibbler.disable()
    nibbler.nibbles = {mock_finding_type_nibble.id: mock_finding_type_nibble}
    network = Network(name="internet")
    xtdb_octopoes_service.ooi_repository.save(network, valid_time)
    finding_type = KATFindingType(id="test")
    xtdb_octopoes_service.ooi_repository.save(finding_type, valid_time)
    event_manager.complete_process_events(xtdb_octopoes_service)

    xtdb_finding_type = xtdb_octopoes_service.ooi_repository.get(finding_type.reference, valid_time)

    result = nibbler.infer([xtdb_finding_type], valid_time)
    event_manager.complete_process_events(xtdb_octopoes_service)

    assert xtdb_finding_type in result


def find_network_url_v2(network: Network, url: URL) -> Iterator[OOI]:
    if len(network.name) == len(str(url.raw)):
        kt = KATFindingType(id="Network and URL have same name length")
        yield kt
        yield Finding(finding_type=kt.reference, ooi=network.reference, proof=url.reference)


def test_nibbles_update(xtdb_octopoes_service: OctopoesService, event_manager: Mock, valid_time: datetime):
    xtdb_octopoes_service.nibbler.nibbles = {find_network_url_nibble.id: find_network_url_nibble}

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

    assert xtdb_octopoes_service.ooi_repository.list_oois({Finding}, valid_time).count == 1
    assert xtdb_octopoes_service.ooi_repository.list_oois({KATFindingType}, valid_time).count == 0

    find_network_url_nibble_v2 = find_network_url_nibble.model_copy(deep=True)
    find_network_url_nibble_v2._payload = getattr(sys.modules[__name__], "find_network_url_v2")
    find_network_url_nibble_v2._checksum = "deadbeef"

    xtdb_octopoes_service.nibbler.update_nibbles(
        valid_time, {find_network_url_nibble_v2.id: find_network_url_nibble_v2}
    )
    event_manager.complete_process_events(xtdb_octopoes_service)

    assert xtdb_octopoes_service.ooi_repository.list_oois({Finding}, valid_time).count == 1
    assert xtdb_octopoes_service.ooi_repository.list_oois({KATFindingType}, valid_time).count == 1


def test_nibble_states(xtdb_octopoes_service: OctopoesService, valid_time: datetime):
    nibble_inis = [nibble._ini for nibble in xtdb_octopoes_service.nibbler.nibbles.values()]
    xtdb_octopoes_service.nibbler.register()
    xtdb_nibble_inis = {ni["id"]: ni for ni in xtdb_octopoes_service.nibbler.nibble_repository.get_all(valid_time)}
    for nibble_ini in nibble_inis:
        assert xtdb_nibble_inis[nibble_ini["id"]] == nibble_ini

    xtdb_octopoes_service.nibbler.toggle_nibbles(["max_url_length_config"], False, valid_time)

    nibble_inis = [nibble._ini for nibble in xtdb_octopoes_service.nibbler.nibbles.values()]
    xtdb_nibble_inis = {ni["id"]: ni for ni in xtdb_octopoes_service.nibbler.nibble_repository.get_all(valid_time)}
    for nibble_ini in nibble_inis:
        assert xtdb_nibble_inis[nibble_ini["id"]] == nibble_ini

    xtdb_octopoes_service.nibbler.nibbles["max_url_length_config"].enabled = True
    xtdb_octopoes_service.nibbler.sync(valid_time)

    nibble_inis = [nibble._ini for nibble in xtdb_octopoes_service.nibbler.nibbles.values()]
    xtdb_nibble_inis = {ni["id"]: ni for ni in xtdb_octopoes_service.nibbler.nibble_repository.get_all(valid_time)}
    for nibble_ini in nibble_inis:
        assert xtdb_nibble_inis[nibble_ini["id"]] == nibble_ini


def test_nibble_origin_deletion_propagation(
    xtdb_octopoes_service: OctopoesService, event_manager: Mock, valid_time: datetime
):
    network = Network(name="internet")
    xtdb_octopoes_service.ooi_repository.save(network, valid_time)
    url = URL(network=network.reference, raw="https://mispo.es/")
    xtdb_octopoes_service.ooi_repository.save(url, valid_time)
    config = Config(ooi=network.reference, bit_id="superkat", config={"max_length": "3"})
    xtdb_octopoes_service.ooi_repository.save(config, valid_time)

    event_manager.complete_process_events(xtdb_octopoes_service)

    assert xtdb_octopoes_service.ooi_repository.list_oois({OOI}, valid_time).count > 3

    xtdb_octopoes_service.ooi_repository.delete(network.reference, valid_time)
    xtdb_octopoes_service.ooi_repository.delete(url.reference, valid_time)
    event_manager.complete_process_events(xtdb_octopoes_service)

    for q in event_manager.queue:
        if q.operation_type == OperationType.CREATE or q.operation_type == OperationType.UPDATE:
            if isinstance(q, OOIDBEvent):
                print(f"CREATE: {q.new_data.reference}")
            elif isinstance(q, OriginDBEvent):
                print(f"CREATE: {q.new_data.id}")
        elif q.operation_type == OperationType.DELETE:
            if isinstance(q, OOIDBEvent):
                print(f"DELETE: {q.old_data.reference}")
            elif isinstance(q, OriginDBEvent):
                print(f"DELETE: {q.old_data.id}")

    assert xtdb_octopoes_service.ooi_repository.list_oois({OOI}, valid_time).count == 1
    assert xtdb_octopoes_service.ooi_repository.list_oois({OOI}, valid_time).items == [config]
