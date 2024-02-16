import os
from datetime import datetime

import pytest

from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.network import Network
from octopoes.models.pagination import Paginated
from octopoes.models.path import Path
from octopoes.repositories.ooi_repository import XTDBOOIRepository
from octopoes.xtdb.query import A, Query

if os.environ.get("CI") != "1":
    pytest.skip("Needs XTDB multinode container.", allow_module_level=True)


def test_list_oois(xtdb_ooi_repository: XTDBOOIRepository, valid_time: datetime):
    xtdb_ooi_repository.save(Network(name="test"), valid_time)

    assert xtdb_ooi_repository.list_oois({Network}, valid_time) == Paginated(count=0, items=[])

    xtdb_ooi_repository.session.commit()

    # list() does not return any OOI without a scan profile
    assert xtdb_ooi_repository.list_oois({Network}, valid_time) == Paginated(count=0, items=[])


def test_complex_query(xtdb_ooi_repository: XTDBOOIRepository, valid_time: datetime):
    network = Network(name="testnetwork")
    network2 = Network(name="testnetwork2")
    xtdb_ooi_repository.save(network, valid_time)
    xtdb_ooi_repository.save(network2, valid_time)
    xtdb_ooi_repository.save(Hostname(network=network2.reference, name="testhostname"), valid_time)
    xtdb_ooi_repository.session.commit()

    # router logic
    object_path = Path.parse("Network.<network[is Hostname]")
    sources = ["Network|testnetwork", "Network|testnetwork2"]
    source_pk_alias = A(object_path.segments[0].source_type, field="primary_key")
    query = (
        Query.from_path(object_path)
        .find(source_pk_alias)
        .pull(Network)
        .where(Network, primary_key=source_pk_alias)
        .where_in(Network, primary_key=sources)
    )

    result = xtdb_ooi_repository.query(query, valid_time)

    assert len(result) == 1
