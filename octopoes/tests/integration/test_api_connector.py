import os
import uuid
from datetime import datetime
from typing import List

import pytest

from octopoes.api.models import Declaration, Observation
from octopoes.config.settings import XTDBType
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import OOI, DeclaredScanProfile, Reference, ScanLevel
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.network import Network
from octopoes.repositories.ooi_repository import XTDBOOIRepository

if os.environ.get("CI") != "1":
    pytest.skip("Needs XTDB multinode container.", allow_module_level=True)


XTDBOOIRepository.xtdb_type = XTDBType.XTDB_MULTINODE


def test_bulk_operations(octopoes_api_connector: OctopoesAPIConnector, valid_time: datetime):
    network = Network(name="test")
    octopoes_api_connector.save_declaration(
        Declaration(
            ooi=network,
            valid_time=valid_time,
        )
    )
    hostnames: List[OOI] = [Hostname(network=network.reference, name=f"test{i}") for i in range(10)]
    octopoes_api_connector.save_observation(
        Observation(
            method="normalizer_id",
            source=network.reference,
            task_id=str(uuid.uuid4()),
            valid_time=valid_time,
            result=hostnames,
        )
    )

    octopoes_api_connector.save_many_scan_profiles(
        [DeclaredScanProfile(reference=ooi.reference, level=ScanLevel.L2) for ooi in hostnames + [network]], valid_time
    )

    assert octopoes_api_connector.list(types={Network}).count == 1
    assert octopoes_api_connector.list(types={Hostname}).count == 10
    assert octopoes_api_connector.list(types={Network, Hostname}).count == 11

    # Delete even-numbered test hostnames
    octopoes_api_connector.delete_many([Reference.from_str(f"Hostname|test|test{i}") for i in range(0, 10, 2)])
    assert octopoes_api_connector.list(types={Network, Hostname}).count == 6
