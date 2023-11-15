import os
import uuid
from datetime import datetime
from ipaddress import ip_address
from typing import List

import pytest
from requests import HTTPError

from octopoes.api.models import Declaration, Observation
from octopoes.config.settings import XTDBType
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import OOI
from octopoes.models.ooi.dns.zone import Hostname, ResolvedHostname
from octopoes.models.ooi.network import IPAddress, IPAddressV4, IPPort, Network
from octopoes.models.ooi.service import IPService, Service
from octopoes.models.ooi.software import Software, SoftwareInstance
from octopoes.models.path import Path
from octopoes.repositories.ooi_repository import XTDBOOIRepository
from octopoes.xtdb.client import XTDBHTTPClient, XTDBSession
from octopoes.xtdb.exceptions import NodeNotFound
from octopoes.xtdb.query import A, Query

if os.environ.get("CI") != "1":
    pytest.skip("Needs XTDB multinode container.", allow_module_level=True)


XTDBOOIRepository.xtdb_type = XTDBType.XTDB_MULTINODE


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


def test_query_for_system_report(octopoes_api_connector: OctopoesAPIConnector, xtdb_session: XTDBSession, valid_time):
    network = Network(name="test")
    octopoes_api_connector.save_declaration(Declaration(ooi=network, valid_time=valid_time))

    hostnames: List[OOI] = [
        Hostname(network=network.reference, name="example.com"),
        Hostname(network=network.reference, name="a.example.com"),
        Hostname(network=network.reference, name="b.example.com"),
        Hostname(network=network.reference, name="c.example.com"),
        Hostname(network=network.reference, name="d.example.com"),
        Hostname(network=network.reference, name="e.example.com"),
    ]

    addresses = [IPAddressV4(network=network.reference, address=ip_address("192.0.2.3"))]
    ports = [
        IPPort(address=addresses[0].reference, protocol="tcp", port=25),
        IPPort(address=addresses[0].reference, protocol="tcp", port=443),
        IPPort(address=addresses[0].reference, protocol="tcp", port=22),
    ]
    services = [Service(name="smtp"), Service(name="https"), Service(name="http"), Service(name="ssh")]
    ip_services = [
        IPService(ip_port=ports[0].reference, service=services[0].reference),
        IPService(ip_port=ports[1].reference, service=services[1].reference),
        IPService(ip_port=ports[2].reference, service=services[3].reference),
    ]

    resolved_hostnames = [
        ResolvedHostname(hostname=hostnames[0].reference, address=addresses[0].reference),
        ResolvedHostname(hostname=hostnames[1].reference, address=addresses[0].reference),
        ResolvedHostname(hostname=hostnames[2].reference, address=addresses[0].reference),
        ResolvedHostname(hostname=hostnames[3].reference, address=addresses[0].reference),
        ResolvedHostname(hostname=hostnames[4].reference, address=addresses[0].reference),
        ResolvedHostname(hostname=hostnames[5].reference, address=addresses[0].reference),
    ]
    software = Software(name="smtp", version="1.1")
    software_instance = SoftwareInstance(ooi=addresses[0].reference, software=software.reference)

    oois = hostnames + addresses + ports + services + ip_services + resolved_hostnames + [software, software_instance]
    octopoes_api_connector.save_observation(
        Observation(method="", source=network.reference, task_id=uuid.uuid4(), valid_time=valid_time, result=oois)
    )

    second_resolved_hostname = A(ResolvedHostname)

    # Find all hostnames that are connected to example.com because they point to the same IpAddressV4. Filter
    # IPAddressV4 where there is an IPService with service name "smtp" on one of its ports.
    query = (
        Query(Hostname)
        .where(Hostname, primary_key="Hostname|test|example.com")
        .where(ResolvedHostname, hostname=Hostname)
        .where(ResolvedHostname, address=IPAddress)
        .where(second_resolved_hostname, hostname=A(Hostname))
        .where(second_resolved_hostname, address=IPAddress)
        .where(IPPort, address=IPAddress)
        .where(IPService, ip_port=IPPort)
        .where(IPService, service=Service)
        .where(Service, name="smtp")
    )

    assert len(xtdb_session.client.query(query)) == 6

    query = (
        Query(Hostname)
        .where(Hostname, primary_key="Hostname|test|example.com")
        .where(ResolvedHostname, hostname=Hostname)
        .where(ResolvedHostname, address=IPAddress)
        .where(second_resolved_hostname, hostname=A(Hostname))
        .where(second_resolved_hostname, address=IPAddress)
        .where(IPPort, address=IPAddress)
        .where(IPService, ip_port=IPPort)
        .where(IPService, service=Service)
        .where(Service, name="http")
    )

    assert len(xtdb_session.client.query(query)) == 0

    # Splitting this query up into two path queries that can be used from the API:

    # Find all hostnames with the same ip address
    query = Query.from_path(
        Path.parse("Hostname.<hostname[is ResolvedHostname].address.<address[is ResolvedHostname].hostname")
    ).where(Hostname, primary_key="Hostname|test|example.com")
    result = xtdb_session.client.query(query)

    assert len(result) == 6
    assert result[0][0]["Hostname/primary_key"] == "Hostname|test|a.example.com"
    assert result[1][0]["Hostname/primary_key"] == "Hostname|test|b.example.com"
    assert result[2][0]["Hostname/primary_key"] == "Hostname|test|c.example.com"
    assert result[3][0]["Hostname/primary_key"] == "Hostname|test|d.example.com"
    assert result[4][0]["Hostname/primary_key"] == "Hostname|test|e.example.com"
    assert result[5][0]["Hostname/primary_key"] == "Hostname|test|example.com"

    # Find all services attached to the hostnames ip address
    query = Query.from_path(Path.parse("IPAddress.<address[is IPPort].<ip_port [is IPService].service")).where(
        IPAddress, primary_key="IPAddressV4|test|192.0.2.3"
    )
    result = xtdb_session.client.query(query)
    assert len(result) == 3

    assert result[0][0]["Service/primary_key"] == "Service|ssh"
    assert result[1][0]["Service/primary_key"] == "Service|smtp"
    assert result[2][0]["Service/primary_key"] == "Service|https"
