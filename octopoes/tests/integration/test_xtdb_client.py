from octopoes.models.ooi.network import Network
from octopoes.xtdb.client import XTDBHTTPClient, XTDBStatus
from octopoes.xtdb.query import Query


def test_create_node(xtdb_http_client: XTDBHTTPClient):
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


def test_query_no_results(xtdb_http_client: XTDBHTTPClient):
    query = Query(Network).where(Network, name="test")

    result = xtdb_http_client.query(str(query))
    assert result == []
