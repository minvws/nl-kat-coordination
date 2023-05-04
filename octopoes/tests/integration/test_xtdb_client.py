import os
from datetime import datetime

import pytest
from requests import HTTPError

from octopoes.config.settings import XTDBType
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.network import Network
from octopoes.repositories.ooi_repository import XTDBOOIRepository
from octopoes.xtdb.client import XTDBHTTPClient, XTDBSession, XTDBStatus
from octopoes.xtdb.query import Query


if os.environ.get("CI") != "1":
    pytest.skip("Needs a CI database.", allow_module_level=True)


XTDBOOIRepository.xtdb_type = XTDBType.XTDB_MULTINODE


def test_node_creation_and_deletion(xtdb_http_client: XTDBHTTPClient):
    xtdb_http_client.create_node()
    assert xtdb_http_client.status() == XTDBStatus(
        version="1.23.0",
        revision="c9ae268855e156f07ac471537445823f011bc320",
        indexVersion=22,
        consumerState=None,
        kvStore="xtdb.rocksdb.RocksKv",
        estimateNumKeys=1,
        size=71255,
    )

    xtdb_http_client.delete_node()

    with pytest.raises(HTTPError):
        assert xtdb_http_client.status()


def test_query_no_results(xtdb_session: XTDBSession):
    query = Query(Network).where(Network, name="test")

    result = xtdb_session.client.query(str(query))
    assert result == []


def test_query_simple_filter(xtdb_session: XTDBSession, valid_time: datetime):
    xtdb_session.put(XTDBOOIRepository.serialize(Network(name="testnetwork")), valid_time)

    query = Query(Network).where(Network, name="test")
    result = xtdb_session.client.query(str(query))
    assert result == []

    xtdb_session.commit()

    query = Query(Network).where(Network, name="test")
    result = xtdb_session.client.query(str(query))
    assert result == []

    query = Query(Network).where(Network, name="testnetwork")
    result = xtdb_session.client.query(str(query))
    assert result == [
        [
            {
                "Network/primary_key": "Network|testnetwork",
                "Network/name": "testnetwork",
                "object_type": "Network",
                "xt/id": "Network|testnetwork",
            }
        ]
    ]


def test_query_not_empty_on_reference_filter_for_hostname(xtdb_session: XTDBSession, valid_time: datetime):
    network = Network(name="testnetwork")
    xtdb_session.put(XTDBOOIRepository.serialize(network), valid_time)
    xtdb_session.put(XTDBOOIRepository.serialize(Hostname(network=network.reference, name="testhostname")), valid_time)
    xtdb_session.put(
        XTDBOOIRepository.serialize(Hostname(network=network.reference, name="secondhostname")), valid_time
    )
    xtdb_session.commit()

    query = Query(Network).where(Hostname, name="testhostname").where(Hostname, network=Network)
    result = xtdb_session.client.query(str(query))
    assert result == [
        [
            {
                "Network/primary_key": "Network|testnetwork",
                "Network/name": "testnetwork",
                "object_type": "Network",
                "xt/id": "Network|testnetwork",
            }
        ]
    ]

    query = query.where(Network, name="testnetwork")
    result = xtdb_session.client.query(str(query))
    assert result == [
        [
            {
                "Network/primary_key": "Network|testnetwork",
                "Network/name": "testnetwork",
                "object_type": "Network",
                "xt/id": "Network|testnetwork",
            }
        ]
    ]


def test_query_empty_on_reference_filter_for_wrong_hostname(xtdb_session: XTDBSession, valid_time: datetime):
    network = Network(name="testnetwork")
    network2 = Network(name="testnetwork2")
    xtdb_session.put(XTDBOOIRepository.serialize(network), valid_time)
    xtdb_session.put(XTDBOOIRepository.serialize(network2), valid_time)
    xtdb_session.put(
        XTDBOOIRepository.serialize(Hostname(network=network2.reference, name="secondhostname")), valid_time
    )
    xtdb_session.commit()

    query = Query(Network).where(Network, name="testnetwork").where(Hostname, name="secondhostname")  # No foreign key
    result = xtdb_session.client.query(str(query))
    assert result == [
        [
            {
                "Network/primary_key": "Network|testnetwork",
                "Network/name": "testnetwork",
                "object_type": "Network",
                "xt/id": "Network|testnetwork",
            }
        ]
    ]

    query = query.where(Hostname, network=Network)  # Add foreign key constraint
    assert xtdb_session.client.query(str(query)) == []

    assert len(xtdb_session.client.query(str(Query(Network)))) == 2
