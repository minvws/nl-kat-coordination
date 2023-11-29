import os
import uuid
from datetime import datetime

import pytest

from octopoes.api.models import Declaration, Observation
from octopoes.config.settings import XTDBType
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import ScanLevel
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.dns.records import NXDOMAIN
from octopoes.models.ooi.network import Network
from octopoes.repositories.ooi_repository import XTDBOOIRepository

if os.environ.get("CI") != "1":
    pytest.skip("Needs XTDB multinode container.", allow_module_level=True)

XTDBOOIRepository.xtdb_type = XTDBType.XTDB_MULTINODE

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

    assert len(octopoes_api_connector.list_origins(task_id={})) < bits_size

    octopoes_api_connector.recalculate_bits()

    assert len(octopoes_api_connector.list_origins(task_id={})) < original_size
