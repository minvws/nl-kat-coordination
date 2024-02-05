import logging
import os
from datetime import datetime, timezone

import pytest
from requests import HTTPError

from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import Reference
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.network import Network
from octopoes.models.path import Path
from octopoes.repositories.ooi_repository import XTDBOOIRepository
from octopoes.repositories.origin_repository import XTDBOriginRepository
from octopoes.xtdb.client import OperationType, XTDBHTTPClient, XTDBSession
from octopoes.xtdb.exceptions import NodeNotFound
from octopoes.xtdb.query import Query
from tests.conftest import seed_system

logger = logging.getLogger(__name__)

if os.environ.get("CI") != "1":
    pytest.skip("Needs XTDB multinode container.", allow_module_level=True)


def test_node_creation_and_deletion(xtdb_http_client: XTDBHTTPClient):
    xtdb_http_client.create_node()
    status = xtdb_http_client.status()

    assert status.indexVersion == 22
    assert status.consumerState is None
    assert status.kvStore == "xtdb.rocksdb.RocksKv"
    assert status.estimateNumKeys >= 1

    xtdb_http_client.delete_node()

    with pytest.raises(HTTPError):
        assert xtdb_http_client.status()


def test_delete_non_existing_node(xtdb_http_client: XTDBHTTPClient):
    with pytest.raises(NodeNotFound):
        xtdb_http_client.delete_node()


def test_query_no_results(xtdb_session: XTDBSession):
    query = Query(Network).where(Network, name="test")

    result = xtdb_session.client.query(query)
    assert result == []


def test_query_simple_filter(xtdb_session: XTDBSession, valid_time: datetime):
    xtdb_session.put(XTDBOOIRepository.serialize(Network(name="testnetwork")), valid_time)

    query = Query(Network).where(Network, name="test")
    result = xtdb_session.client.query(query)
    assert result == []

    xtdb_session.commit()

    query = Query(Network).where(Network, name="test")
    result = xtdb_session.client.query(query)
    assert result == []

    query = Query(Network).where(Network, name="testnetwork")
    result = xtdb_session.client.query(query)
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

    query = """{:query {:find [(pull ?3b1ebf3a-3cc1-4e35-8c5f-e8173e55b623 [*])] :where [
    [ ?3b1ebf3a-3cc1-4e35-8c5f-e8173e55b623 :Network/name "testnetwork" ]
    [ ?3b1ebf3a-3cc1-4e35-8c5f-e8173e55b623 :object_type "Network" ]] limit 50 offset 0}}"""

    assert len(xtdb_session.client.query(query)) == 1


def test_query_not_empty_on_reference_filter_for_hostname(xtdb_session: XTDBSession, valid_time: datetime):
    network = Network(name="testnetwork")
    xtdb_session.put(XTDBOOIRepository.serialize(network), valid_time)
    xtdb_session.put(XTDBOOIRepository.serialize(Hostname(network=network.reference, name="testhostname")), valid_time)
    xtdb_session.put(
        XTDBOOIRepository.serialize(Hostname(network=network.reference, name="secondhostname")), valid_time
    )
    xtdb_session.commit()

    query = Query(Network).where(Hostname, name="testhostname").where(Hostname, network=Network)
    result = xtdb_session.client.query(query)
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
    result = xtdb_session.client.query(query)
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
    result = xtdb_session.client.query(query)
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
    assert xtdb_session.client.query(query) == []

    assert len(xtdb_session.client.query(str(Query(Network)))) == 2


def test_entity_history(xtdb_session: XTDBSession, valid_time: datetime):
    network = Network(name="testnetwork")
    xtdb_session.put(XTDBOOIRepository.serialize(network), datetime.now(timezone.utc))
    xtdb_session.commit()

    xtdb_session.add((OperationType.DELETE, str(network.reference), datetime.now(timezone.utc)))
    xtdb_session.commit()

    xtdb_session.put(XTDBOOIRepository.serialize(network), datetime.now(timezone.utc))
    xtdb_session.commit()

    history = xtdb_session.client.get_entity_history(str(network.reference), with_docs=True)
    assert len(history) == 3

    assert history[0].document is not None
    assert history[1].document is None
    assert history[2].document is not None


def test_query_for_system_report(
    octopoes_api_connector: OctopoesAPIConnector,
    xtdb_ooi_repository: XTDBOOIRepository,
    xtdb_origin_repository: XTDBOriginRepository,
    xtdb_session: XTDBSession,
    valid_time,
):
    seed_system(xtdb_ooi_repository, xtdb_origin_repository, valid_time)

    # Find all hostnames with the same ip address
    query = Query.from_path(
        Path.parse("Hostname.<hostname[is ResolvedHostname].address.<address[is ResolvedHostname].hostname")
    ).where(Hostname, primary_key="Hostname|test|example.com")
    result = xtdb_session.client.query(query)

    assert len(result) == 10
    pks = [x[0]["Hostname/primary_key"] for x in result]

    assert pks.count("Hostname|test|a.example.com") == 1
    assert pks.count("Hostname|test|b.example.com") == 1
    assert pks.count("Hostname|test|c.example.com") == 2  # Duplicated through ipv6
    assert pks.count("Hostname|test|d.example.com") == 2  # Duplicated through ipv6
    assert pks.count("Hostname|test|e.example.com") == 1
    assert pks.count("Hostname|test|f.example.com") == 1
    assert pks.count("Hostname|test|example.com") == 2  # Duplicated through ipv6

    # Find all services attached to the hostnames ip address
    query = Query.from_path(
        Path.parse(
            "Hostname.<hostname[is ResolvedHostname].address.<address[is IPPort].<ip_port [is IPService].service"
        )
    ).where(Hostname, primary_key="Hostname|test|example.com")
    result = xtdb_session.client.query(query)
    assert len(result) == 4

    pks = {x[0]["Service/primary_key"] for x in result}
    assert pks == {"Service|ssh", "Service|smtp", "Service|https", "Service|http"}

    # Queries performed in Rocky's system report
    ips = octopoes_api_connector.query(
        "Hostname.<hostname[is ResolvedHostname].address", valid_time, "Hostname|test|c.example.com"
    )

    ip_services = {}

    for ip in ips:
        ip_services[str(ip.address)] = {
            "hostnames": [
                str(x.name)
                for x in octopoes_api_connector.query(
                    "IPAddress.<address[is ResolvedHostname].hostname",
                    valid_time,
                    ip.reference,
                )
            ],
            "services": list(
                set(
                    [
                        str(x.name)
                        for x in octopoes_api_connector.query(
                            "IPAddress.<address[is IPPort].<ip_port [is IPService].service",
                            valid_time,
                            ip.reference,
                        )
                    ]
                ).union(
                    set(
                        [
                            str(x.name)
                            for x in octopoes_api_connector.query(
                                "IPAddress.<address[is IPPort].<ooi [is SoftwareInstance].software",
                                valid_time,
                                ip.reference,
                            )
                        ]
                    )
                )
            ),
            "websites": [
                str(x.hostname)
                for x in octopoes_api_connector.query(
                    "IPAddress.<address[is IPPort].<ip_port [is IPService].<ip_service [is Website]",
                    valid_time,
                    ip.reference,
                )
                if x.hostname == Reference.from_str("Hostname|test|a.example.com")
            ],
        }

    assert len(ips) == 2
    assert len(ip_services["192.0.2.3"]["hostnames"]) == 6
    assert len(ip_services["192.0.2.3"]["services"]) == 4
    assert len(ip_services["192.0.2.3"]["websites"]) == 1
    assert ip_services["192.0.2.3"]["websites"][0] == "Hostname|test|a.example.com"

    assert len(ip_services["3e4d:64a2:cb49:bd48:a1ba:def3:d15d:9230"]["hostnames"]) == 4
    assert len(ip_services["3e4d:64a2:cb49:bd48:a1ba:def3:d15d:9230"]["services"]) == 1
    assert len(ip_services["3e4d:64a2:cb49:bd48:a1ba:def3:d15d:9230"]["websites"]) == 0


def test_query_for_web_system_report(
    octopoes_api_connector: OctopoesAPIConnector,
    xtdb_ooi_repository: XTDBOOIRepository,
    xtdb_origin_repository: XTDBOriginRepository,
    xtdb_session: XTDBSession,
    valid_time: datetime,
):
    seed_system(xtdb_ooi_repository, xtdb_origin_repository, valid_time)
    web_hostname = Hostname(network=Network(name="test").reference, name="example.com")
    second_web_hostname = Hostname(network=Network(name="test").reference, name="a.example.com")

    query = "Hostname.<ooi[is Finding].finding_type"
    assert (
        len(octopoes_api_connector.query(query, valid_time, web_hostname.reference)) == 0
    )  # We should not consider Internetnl finding types

    query = "Hostname.<hostname[is Website].<website[is HTTPResource].<ooi[is Finding].finding_type"
    resources_finding_types = octopoes_api_connector.query(query, valid_time, web_hostname.reference)

    assert len(resources_finding_types) == 1
    ids = [x.id for x in resources_finding_types]
    assert "KAT-NO-CSP" in ids

    query = "Hostname.<netloc[is HostnameHTTPURL].<ooi[is Finding].finding_type"
    web_url_finding_types = octopoes_api_connector.query(query, valid_time, web_hostname.reference)
    assert len(web_url_finding_types) == 1
    assert web_url_finding_types[0].id == "KAT-NO-HTTPS-REDIRECT"

    query = "Hostname.<hostname[is Website].<ooi[is Finding].finding_type"
    assert len(octopoes_api_connector.query(query, valid_time, web_hostname.reference)) == 0
    assert len(octopoes_api_connector.query(query, valid_time, second_web_hostname.reference)) == 1

    query = "Hostname.<hostname[is Website].<website[is SecurityTXT]"
    assert len(octopoes_api_connector.query(query, valid_time, web_hostname.reference)) == 0

    # a.example.com has a SecurityTXT
    assert len(octopoes_api_connector.query(query, valid_time, second_web_hostname.reference)) == 1

    query = "Hostname.<hostname[is ResolvedHostname].address.<address[is IPPort]"
    assert len(octopoes_api_connector.query(query, valid_time, web_hostname.reference)) == 4

    query = "Hostname.<hostname[is Website].certificate.<ooi[is Finding].finding_type"
    assert len(octopoes_api_connector.query(query, valid_time, web_hostname.reference)) == 0
