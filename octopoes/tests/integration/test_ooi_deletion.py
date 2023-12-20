import os
import time
import uuid
from datetime import datetime
from unittest.mock import Mock

import pytest

from octopoes.api.models import Declaration, Observation
from octopoes.config.settings import XTDBType
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.core.service import OctopoesService
from octopoes.events.events import OOIDBEvent, OriginDBEvent
from octopoes.models import ScanLevel
from octopoes.models.ooi.dns.records import NXDOMAIN
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.network import Network
from octopoes.models.origin import Origin, OriginType
from octopoes.repositories.ooi_repository import XTDBOOIRepository

if os.environ.get("CI") != "1":
    pytest.skip("Needs XTDB multinode container.", allow_module_level=True)

XTDBOOIRepository.xtdb_type = XTDBType.XTDB_MULTINODE


def printer(arg1, arg2):
    print(arg1)
    for k in arg2:
        print(k)
    print()


def test_hostname_nxd_ooi(octopoes_api_connector: OctopoesAPIConnector, valid_time: datetime):
    network = Network(name="internet")
    octopoes_api_connector.save_declaration(Declaration(ooi=network, valid_time=valid_time, level=ScanLevel.L2))
    dns = "mispo.es"
    hostname = Hostname(network=network.reference, name=dns)
    octopoes_api_connector.save_declaration(Declaration(ooi=hostname, valid_time=valid_time, level=ScanLevel.L2))

    original_size = len(octopoes_api_connector.list_origins(task_id={}))
    assert original_size >= 2
    octopoes_api_connector.recalculate_bits()
    bits_size = len(octopoes_api_connector.list_origins(task_id={}))
    assert bits_size >= original_size

    nxd = NXDOMAIN(hostname=hostname.reference)
    octopoes_api_connector.save_observation(
        Observation(
            method="normalizer_id",
            source=hostname.reference,
            task_id=uuid.uuid4(),
            valid_time=valid_time,
            result=[nxd],
        )
    )
    octopoes_api_connector.recalculate_bits()

    octopoes_api_connector.delete(network.reference)
    octopoes_api_connector.delete(hostname.reference)

    # This sleep is here because otherwise on some systems this test will fail
    # Delete when issue #2083 is resolved...
    time.sleep(1)
    assert len(octopoes_api_connector.list_origins(task_id={})) < bits_size

    octopoes_api_connector.recalculate_bits()

    assert len(octopoes_api_connector.list_origins(task_id={})) < original_size


def test_events_created_through_crud(xtdb_octopoes_service: OctopoesService, event_manager: Mock, valid_time: datetime):
    network = Network(name="internet")

    origin = Origin(
        origin_type=OriginType.DECLARATION,
        method="manual",
        source=network.reference,
        result=[network.reference],
        task_id=str(uuid.uuid4()),
    )
    xtdb_octopoes_service.save_origin(origin, [network], valid_time)
    xtdb_octopoes_service.commit()

    assert event_manager.publish.call_count == 2

    call1 = event_manager.publish.call_args_list[0]
    call2 = event_manager.publish.call_args_list[1]

    assert isinstance(call1.args[0], OOIDBEvent)
    assert isinstance(call2.args[0], OriginDBEvent)

    assert call1.args[0].old_data is None
    assert call1.args[0].new_data == network
    assert call1.args[0].operation_type.value == "create"

    assert call2.args[0].old_data is None
    assert call2.args[0].new_data == origin
    assert call2.args[0].operation_type.value == "create"

    xtdb_octopoes_service.ooi_repository.delete(network.reference, valid_time)
    xtdb_octopoes_service.commit()

    assert event_manager.publish.call_count == 3  # Origin will be deleted by the worker due to the OOI delete event
    call3 = event_manager.publish.call_args_list[2]
    assert isinstance(call3.args[0], OOIDBEvent)
    assert call3.args[0].operation_type.value == "delete"


def test_events_created_in_worker_during_handling(
    xtdb_octopoes_service: OctopoesService, event_manager: Mock, valid_time: datetime
):
    network = Network(name="internet")

    origin = Origin(
        origin_type=OriginType.DECLARATION,
        method="manual",
        source=network.reference,
        result=[network.reference],
        task_id=str(uuid.uuid4()),
    )
    xtdb_octopoes_service.save_origin(origin, [network], valid_time)
    xtdb_octopoes_service.commit()
    xtdb_octopoes_service.ooi_repository.delete(network.reference, valid_time)
    xtdb_octopoes_service.commit()

    assert event_manager.publish.call_count == 3
    event = event_manager.publish.call_args_list[2].args[0]  # OOIDelete event

    # for event in event_manager.get_events():
    #     xtdb_octopoes_service.process_event(event)

    xtdb_octopoes_service.process_event(event)
    xtdb_octopoes_service.commit()

    assert event_manager.publish.call_count == 4  # Handling OOI delete event triggers Origin delete event

    call = event_manager.publish.call_args_list[3]
    assert isinstance(call.args[0], OriginDBEvent)
    assert call.args[0].operation_type.value == "delete"
