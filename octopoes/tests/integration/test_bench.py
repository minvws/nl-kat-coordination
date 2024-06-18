import os
from datetime import datetime

import pytest

from octopoes.core.service import OctopoesService
from octopoes.repositories.ooi_repository import XTDBOOIRepository
from octopoes.repositories.origin_repository import XTDBOriginRepository
from tests.conftest import seed_system

if os.environ.get("CI") != "1":
    pytest.skip("Needs XTDB multinode container.", allow_module_level=True)


@pytest.mark.slow
def test_run_inference_bench(
    xtdb_ooi_repository: XTDBOOIRepository,
    xtdb_origin_repository: XTDBOriginRepository,
    xtdb_octopoes_service: OctopoesService,
    valid_time: datetime,
):
    hostname_range = range(0, 20)
    for x in hostname_range:
        seed_system(
            xtdb_ooi_repository,
            xtdb_origin_repository,
            valid_time,
            test_hostname=f"{x}.com",
            test_ip=f"192.0.{x % 7}.{x % 13}",
            test_ipv6=f"{x % 7}e4d:64a2:cb49:bd48:a1ba:def3:d15d:{x % 5}230",
        )

    output = xtdb_octopoes_service.recalculate_bits()
    assert output == 2272

    xtdb_octopoes_service.commit()
    output = xtdb_octopoes_service.recalculate_bits()

    xtdb_octopoes_service.commit()

    assert output == 2272
