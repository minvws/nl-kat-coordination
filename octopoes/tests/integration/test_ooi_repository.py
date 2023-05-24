import os
from datetime import datetime

import pytest

from octopoes.config.settings import XTDBType
from octopoes.models.ooi.network import Network
from octopoes.models.pagination import Paginated
from octopoes.repositories.ooi_repository import XTDBOOIRepository

if os.environ.get("CI") != "1":
    pytest.skip("Needs XTDB multinode container.", allow_module_level=True)


XTDBOOIRepository.xtdb_type = XTDBType.XTDB_MULTINODE


def test_list_oois(xtdb_ooi_repository: XTDBOOIRepository, valid_time: datetime):
    xtdb_ooi_repository.save(Network(name="test"), valid_time)

    assert xtdb_ooi_repository.list({Network}, valid_time) == Paginated(count=0, items=[])

    xtdb_ooi_repository.session.commit()

    # list() does not return any OOI without a scan profile
    assert xtdb_ooi_repository.list({Network}, valid_time) == Paginated(count=0, items=[])
