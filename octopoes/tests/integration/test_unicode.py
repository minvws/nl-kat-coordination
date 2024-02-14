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

use_unicode = False
names = ["🐱", "★.com", "🐈"] if use_unicode else ["cat", "xn--p3h.com", "boefje"]


def test_unicode_operations(octopoes_api_connector: OctopoesAPIConnector, valid_time: datetime):
    network = Network(name=names[0])
    octopoes_api_connector.save_declaration(
        Declaration(
            ooi=network,
            valid_time=valid_time,
        )
    )
    hostname = Hostname(network=network.reference, name=names[1])
    task_id = uuid.uuid4()

    octopoes_api_connector.save_observation(
        Observation(
            method=names[2],
            source=network.reference,
            task_id=task_id,
            valid_time=valid_time,
            result=[hostname],
        )
    )

    scanprof = DeclaredScanProfile(reference=hostname.reference, level=ScanLevel.L2)
    octopoes_api_connector.save_scan_profile(scanprof, valid_time)

    assert octopoes_api_connector.list(types={Network}).count == 1
    assert octopoes_api_connector.list(types={Hostname}).count == 1
    assert octopoes_api_connector.list(types={Network, Hostname}).count == 2

    origins = octopoes_api_connector.list_origins(task_id=task_id)
    assert origins[0].dict() == {
        "method": names[2],
        "origin_type": OriginType.OBSERVATION,
        "source": network.reference,
        "result": [hostname.reference],
        "task_id": task_id,
    }

    assert len(octopoes_api_connector.list_origins(result=hostname.reference)) == 1
