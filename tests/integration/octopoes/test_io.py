import json
import os
import time
import uuid
from datetime import datetime
from operator import itemgetter

import pytest

from octopoes.api.models import Declaration, Observation
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import DeclaredScanProfile, ScanLevel
from octopoes.models.ooi.network import Network
from octopoes.models.origin import OriginType

if os.environ.get("CI") != "1":
    pytest.skip("Needs XTDB multinode container.", allow_module_level=True)


def test_io(xtdb_octopoes_api_connector: OctopoesAPIConnector, valid_time: datetime):
    network = Network(name="internet")
    xtdb_octopoes_api_connector.save_declaration(Declaration(ooi=network, valid_time=valid_time))
    scan_profile = DeclaredScanProfile(reference=network.reference, level=ScanLevel.L2)
    xtdb_octopoes_api_connector.save_scan_profile(scan_profile, valid_time)

    assert xtdb_octopoes_api_connector.list_objects(types={Network}, valid_time=valid_time).count == 1
    network_object = xtdb_octopoes_api_connector.list_objects(types={Network}, valid_time=valid_time).items[0]
    assert network_object.name == "internet"
    assert network_object.reference == network.reference

    txops = xtdb_octopoes_api_connector.export_all()
    transactions = list(map(itemgetter("txOps"), txops))
    data = {
        "object_type": "Network",
        "user_id": None,
        "Network/primary_key": "Network|internet",
        "Network/name": "internet",
        "xt/id": "Network|internet",
    }
    dt = valid_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    target = json.loads(json.dumps(["put", data, dt]))
    assert any([target in tx for tx in transactions])

    res = xtdb_octopoes_api_connector.import_new(json.dumps(txops))
    assert res == {"detail": len(transactions)}

    assert xtdb_octopoes_api_connector.list_objects(types={Network}, valid_time=valid_time).count == 1
    network_object = xtdb_octopoes_api_connector.list_objects(types={Network}, valid_time=valid_time).items[0]
    assert network_object.name == "internet"
    assert network_object.reference == network.reference

    network_cat = f"""
    [
      {{
        "txId": 101,
        "txTime": "2024-04-01T13:37:00Z",
        "txOps": [
          [
            "put",
            {{
              "object_type": "Network",
              "user_id": null,
              "Network/primary_key": "Network|😸",
              "Network/name": "😸",
              "xt/id": "Network|😸"
            }},
            "{dt}"
          ]
        ]
      }}
    ]
    """

    res = xtdb_octopoes_api_connector.import_add(network_cat)
    assert res == {"detail": 1}
    time.sleep(3)

    assert len(list(map(itemgetter("txOps"), xtdb_octopoes_api_connector.export_all()))) > len(transactions)


def test_duplicate_origin_result_filter(xtdb_octopoes_api_connector: OctopoesAPIConnector, valid_time: datetime):
    network1 = Network(name="1")
    network2 = Network(name="2")
    xtdb_octopoes_api_connector.save_observation(
        Observation(
            method="normalizer_id",
            source=network1.reference,
            source_method=None,
            task_id=uuid.uuid4(),
            valid_time=valid_time,
            result=[network1, network1, network2, network2],
        )
    )
    origins = xtdb_octopoes_api_connector.list_origins(
        origin_type=OriginType.OBSERVATION, task_id=None, valid_time=valid_time
    )

    assert len(origins) == 1
    assert len(origins[0].result) == 2
    assert origins[0].result[0] == network1.reference
    assert origins[0].result[1] == network2.reference
