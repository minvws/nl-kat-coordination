import json
import uuid

import pytest
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models.origin import OriginType
from tests.conftest import seed_system

from boefjes.clients.bytes_client import BytesAPIClient
from tests.loading import get_dummy_data, get_boefje_meta, get_raw_data_meta, get_normalizer_meta
from tools.upgrade_v1_16_0 import upgrade


@pytest.mark.slow
def test_migration(octopoes_api_connector: OctopoesAPIConnector, bytes_client: BytesAPIClient, valid_time):
    hostname_range = range(0, 20)

    for x in hostname_range:
        seed_system(
            octopoes_api_connector,
            valid_time,
            test_hostname=f"{x}.com",
            test_ip=f"192.0.{x % 7}.{x % 13}",
            test_ipv6=f"{x % 7}e4d:64a2:cb49:bd48:a1ba:def3:d15d:{x % 5}230",
        )

    export = octopoes_api_connector.export_all()

    # Drop the source method field to test the migration
    for tx in export:
        if "txOps" in tx and len(tx["txOps"]) > 1 and len(tx["txOps"][1]) > 1 and "source_method" in tx["txOps"][1][1]:
            del tx["txOps"][1][1]["source_method"]

    octopoes_api_connector.import_new(json.dumps(export))
    bytes_client.login()

    raw = b"1234567890"

    for origin in octopoes_api_connector.list_origins(valid_time, origin_type=OriginType.OBSERVATION):
        boefje_meta = get_boefje_meta(uuid.uuid4())
        bytes_client.save_boefje_meta(boefje_meta)
        raw_data_id = bytes_client.save_raw(boefje_meta.id, raw)

        normalizer_meta = get_normalizer_meta(boefje_meta, raw_data_id)
        normalizer_meta.id = origin.task_id

        bytes_client.save_normalizer_meta(normalizer_meta)

    total_processed, total_failed = upgrade(valid_time)

    assert total_processed == 0
    assert total_failed == 0
