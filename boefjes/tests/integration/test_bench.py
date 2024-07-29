import json
import uuid

import pytest

from boefjes.sql.organisation_storage import SQLOrganisationStorage
from tools.upgrade_v1_16_0 import upgrade

from boefjes.clients.bytes_client import BytesAPIClient
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models.origin import OriginType
from tests.conftest import seed_system
from tests.loading import get_boefje_meta, get_normalizer_meta


@pytest.mark.slow
def test_migration(octopoes_api_connector: OctopoesAPIConnector, bytes_client: BytesAPIClient, organisation_repository: SQLOrganisationStorage, valid_time):
    hostname_range = range(0, 30)

    for x in hostname_range:
        seed_system(
            octopoes_api_connector,
            valid_time,
            test_hostname=f"{x}.com",
            test_ip=f"192.0.{x % 7}.{x % 13}",
            test_ipv6=f"{x % 7}e4d:64a2:cb49:bd48:a1ba:def3:d15d:{x % 5}230",
        )

    raw = b"1234567890"

    for origin in octopoes_api_connector.list_origins(valid_time, origin_type=OriginType.OBSERVATION):
        boefje_meta = get_boefje_meta(uuid.uuid4(), boefje_id="bench_boefje")
        bytes_client.save_boefje_meta(boefje_meta)
        raw_data_id = bytes_client.save_raw(boefje_meta.id, raw)

        normalizer_meta = get_normalizer_meta(boefje_meta, raw_data_id)
        normalizer_meta.id = origin.task_id
        normalizer_meta.normalizer.id = "kat_nmap_normalize"

        bytes_client.save_normalizer_meta(normalizer_meta)

    export = []

    # Drop the source method field to test the migration
    for tx in octopoes_api_connector.export_all():
        if "txOps" in tx:
            ops = []
            for tx_op in tx["txOps"]:
                if "source_method" in tx_op[1]:
                    del tx_op[1]["source_method"]

                ops.append(tx_op)

            tx["txOps"] = ops

        export.append(tx)

    octopoes_api_connector.import_new(json.dumps(export))
    bytes_client.login()
    total_processed, total_failed = upgrade(organisation_repository, valid_time)

    assert total_processed == len(hostname_range)
    assert total_failed == 0

    observation = octopoes_api_connector.list_origins(valid_time, origin_type=OriginType.OBSERVATION)[0]

    assert observation.method == normalizer_meta.normalizer.id
    assert observation.source_method == boefje_meta.boefje.id
