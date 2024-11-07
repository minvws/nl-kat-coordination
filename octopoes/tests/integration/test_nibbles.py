import os
import sys
from datetime import datetime
from unittest.mock import Mock

import pytest
from nibbles.definitions import NibbleDefinition, NibbleParameterDefinition

from octopoes.core.service import OctopoesService
from octopoes.models import OOI, ScanLevel
from octopoes.models.ooi.network import Network

if os.environ.get("CI") != "1":
    pytest.skip("Needs XTDB multinode container.", allow_module_level=True)

NMAX = 13
dummy_nibble = NibbleDefinition(name="dummy", signature=[NibbleParameterDefinition(ooi_type=Network)])


def dummy(network: Network):
    global NMAX
    if len(network.name) < NMAX:
        new_name = network.name + "I"
        return Network(name=new_name)


dummy_nibble.payload = getattr(sys.modules[__name__], "dummy")


def test_dummy_nibble(xtdb_octopoes_service: OctopoesService, event_manager: Mock, valid_time: datetime):
    xtdb_octopoes_service.nibbles.nibbles = [dummy_nibble]
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

    ctx = 1 + NMAX - len(network.name)
    assert xtdb_octopoes_service.ooi_repository.list_oois({Network}, valid_time).count == ctx
    assert xtdb_octopoes_service.ooi_repository.list_oois({OOI}, valid_time).count == 3 * ctx
