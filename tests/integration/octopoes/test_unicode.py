import os
import uuid
from datetime import datetime

import pytest

from octopoes.api.models import Declaration, Observation
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import DeclaredScanProfile, ScanLevel
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.network import Network
from octopoes.models.origin import OriginType

if os.environ.get("CI") != "1":
    pytest.skip("Needs XTDB multinode container.", allow_module_level=True)

NAMES = ["🐱", "★.com", "🐈"]


def test_unicode_network(xtdb_octopoes_api_connector: OctopoesAPIConnector, valid_time: datetime):
    network = Network(name=NAMES[0])
    xtdb_octopoes_api_connector.save_declaration(Declaration(ooi=network, valid_time=valid_time))
    scan_profile = DeclaredScanProfile(reference=network.reference, level=ScanLevel.L2)
    xtdb_octopoes_api_connector.save_scan_profile(scan_profile, valid_time)

    assert xtdb_octopoes_api_connector.list_objects(types={Network}, valid_time=valid_time).count == 1
    network_object = xtdb_octopoes_api_connector.list_objects(types={Network}, valid_time=valid_time).items[0]
    assert network_object.name == NAMES[0]
    assert network_object.reference == network.reference


def test_unicode_hostname(xtdb_octopoes_api_connector: OctopoesAPIConnector, valid_time: datetime):
    network = Network(name=NAMES[0])
    xtdb_octopoes_api_connector.save_declaration(Declaration(ooi=network, valid_time=valid_time))

    with pytest.raises(ValueError):
        Hostname(network=network.reference, name="%@.com")

    hostname = Hostname(network=network.reference, name=NAMES[1])
    task_id = uuid.uuid4()

    xtdb_octopoes_api_connector.save_observation(
        Observation(
            method=NAMES[2],
            source=network.reference,
            source_method="test",
            task_id=task_id,
            valid_time=valid_time,
            result=[hostname],
        )
    )

    scan_profile = DeclaredScanProfile(reference=hostname.reference, level=ScanLevel.L2)
    xtdb_octopoes_api_connector.save_scan_profile(scan_profile, valid_time)
    scan_profile = DeclaredScanProfile(reference=network.reference, level=ScanLevel.L2)
    xtdb_octopoes_api_connector.save_scan_profile(scan_profile, valid_time)

    assert xtdb_octopoes_api_connector.list_objects(types={Network, Hostname}, valid_time=valid_time).count == 2

    network_object = xtdb_octopoes_api_connector.list_objects(types={Network}, valid_time=valid_time).items[0]
    assert network_object.name == NAMES[0]
    assert network_object.reference == network.reference

    hostname_object = xtdb_octopoes_api_connector.list_objects(types={Hostname}, valid_time=valid_time).items[0]
    assert hostname_object.name == NAMES[1].encode("idna").decode()
    assert hostname_object.reference == hostname.reference

    origins = xtdb_octopoes_api_connector.list_origins(task_id=task_id, valid_time=valid_time)
    assert origins[0].dict() == {
        "method": NAMES[2],
        "origin_type": OriginType.OBSERVATION,
        "source": network.reference,
        "source_method": "test",
        "result": [hostname.reference],
        "task_id": task_id,
    }

    assert len(xtdb_octopoes_api_connector.list_origins(result=hostname.reference, valid_time=valid_time)) == 1
