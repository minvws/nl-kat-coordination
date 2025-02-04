import os
import uuid
from datetime import datetime, timezone
from ipaddress import ip_address

import pytest

from octopoes.api.models import Declaration, Observation
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import OOI, DeclaredScanProfile, Reference, ScanLevel
from octopoes.models.exception import ObjectNotFoundException
from octopoes.models.ooi.dns.records import DNSAAAARecord, DNSARecord, DNSMXRecord, DNSNSRecord
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.findings import Finding, KATFindingType, RiskLevelSeverity
from octopoes.models.ooi.network import IPAddressV4, IPAddressV6, IPPort, Network, PortState, Protocol
from octopoes.models.ooi.service import IPService, Service
from octopoes.models.ooi.web import Website
from octopoes.models.origin import OriginType

if os.environ.get("CI") != "1":
    pytest.skip("Needs XTDB multinode container.", allow_module_level=True)


def test_bulk_operations(octopoes_api_connector: OctopoesAPIConnector, valid_time: datetime):
    network = Network(name="test")
    octopoes_api_connector.save_declaration(Declaration(ooi=network, valid_time=valid_time))
    hostnames = [Hostname(network=network.reference, name=f"test{i}") for i in range(10)]
    task_id = uuid.uuid4()

    octopoes_api_connector.save_observation(
        Observation(
            method="normalizer_id",
            source=network.reference,
            source_method="manual",
            task_id=task_id,
            valid_time=valid_time,
            result=hostnames,
        )
    )

    octopoes_api_connector.save_many_scan_profiles(
        [DeclaredScanProfile(reference=ooi.reference, level=ScanLevel.L2) for ooi in hostnames + [network]], valid_time
    )

    assert octopoes_api_connector.list_objects(types={Network}, valid_time=valid_time).count == 1
    assert octopoes_api_connector.list_objects(types={Hostname}, valid_time=valid_time).count == 10
    assert octopoes_api_connector.list_objects(types={Network, Hostname}, valid_time=valid_time).count == 11

    assert len(octopoes_api_connector.list_origins(task_id=uuid.uuid4(), valid_time=valid_time)) == 0
    origins = octopoes_api_connector.list_origins(task_id=task_id, valid_time=valid_time)
    assert len(origins) == 1
    assert origins[0].model_dump() == {
        "method": "normalizer_id",
        "origin_type": OriginType.OBSERVATION,
        "source": network.reference,
        "source_method": "manual",
        "result": [hostname.reference for hostname in hostnames],
        "task_id": task_id,
    }

    assert len(octopoes_api_connector.list_origins(result=hostnames[0].reference, valid_time=valid_time)) == 1

    # Delete even-numbered test hostnames
    octopoes_api_connector.delete_many(
        [Reference.from_str(f"Hostname|test|test{i}") for i in range(0, 10, 2)], valid_time=valid_time
    )
    assert octopoes_api_connector.list_objects(types={Network, Hostname}, valid_time=valid_time).count == 6

    with pytest.raises(ObjectNotFoundException):
        octopoes_api_connector.delete_many(["test"], valid_time=valid_time)

    assert len(octopoes_api_connector.list_origins(origin_type=OriginType.DECLARATION, valid_time=valid_time)) == 1

    octopoes_api_connector.save_many_declarations([Declaration(ooi=h, valid_time=valid_time) for h in hostnames])

    assert (
        len(octopoes_api_connector.list_origins(origin_type=OriginType.DECLARATION, valid_time=valid_time))
        == len(hostnames) + 1
    )

    bulk_hostnames = octopoes_api_connector.load_objects_bulk({x.reference for x in hostnames}, valid_time)

    assert len(bulk_hostnames) == 10

    for hostname in hostnames:
        assert bulk_hostnames[hostname.reference].scan_profile is not None


def test_history(octopoes_api_connector: OctopoesAPIConnector):
    network = Network(name="test")
    first_seen = datetime(year=2020, month=10, day=10, tzinfo=timezone.utc)  # XTDB only returns a precision of seconds
    octopoes_api_connector.save_declaration(Declaration(ooi=network, valid_time=first_seen))
    octopoes_api_connector.delete(network.reference, datetime(year=2020, month=10, day=11, tzinfo=timezone.utc))
    last_seen = datetime(year=2020, month=10, day=12, tzinfo=timezone.utc)
    octopoes_api_connector.save_declaration(Declaration(ooi=network, valid_time=last_seen))

    history = octopoes_api_connector.get_history(network.reference, with_docs=True)
    assert len(history) == 3
    assert history[0].document is not None
    assert history[1].document is None
    assert history[2].document is not None

    assert len(octopoes_api_connector.get_history(network.reference, has_doc=False)) == 1

    with_doc = octopoes_api_connector.get_history(network.reference, has_doc=True)
    assert len(with_doc) == 2
    assert not all([x.document for x in with_doc])

    assert len(octopoes_api_connector.get_history(network.reference, offset=1)) == 2
    assert len(octopoes_api_connector.get_history(network.reference, limit=2)) == 2

    first_and_last = octopoes_api_connector.get_history(network.reference, has_doc=True, indices=[0, -1])
    assert len(first_and_last) == 2
    assert first_and_last[0].valid_time == first_seen
    assert first_and_last[1].valid_time == last_seen


def test_query(octopoes_api_connector: OctopoesAPIConnector, valid_time: datetime):
    network = Network(name="test")
    octopoes_api_connector.save_declaration(Declaration(ooi=network, valid_time=valid_time))

    hostnames: list[OOI] = [Hostname(network=network.reference, name=f"test{i}") for i in range(10)]

    addresses = [IPAddressV6(network=network.reference, address=ip_address("3e4d:64a2:cb49:bd48:a1ba:def3:d15d:9230"))]
    v4_addresses = [IPAddressV4(network=network.reference, address=ip_address("127.0.0.1"))]
    ports = [
        IPPort(address=addresses[0].reference, protocol="tcp", port=22),
        IPPort(address=v4_addresses[0].reference, protocol="tcp", port=443),
    ]
    services = [Service(name="https")]
    ip_services = [IPService(ip_port=ports[0].reference, service=services[0].reference)]

    dns_ns_records = [
        DNSNSRecord(hostname=hostnames[i].reference, name_server_hostname=hostnames[3].reference, value="test")
        for i in range(3)
    ]
    dns_aaaa_records = [DNSAAAARecord(hostname=hostnames[3].reference, address=addresses[0].reference, value="test")]
    dns_mx_records = [DNSMXRecord(hostname=hostnames[1].reference, mail_hostname=hostnames[3].reference, value="test")]
    dns_a_records = [DNSARecord(hostname=hostnames[3].reference, address=v4_addresses[0].reference, value="test")]
    sites = [Website(ip_service=ip_services[0].reference, hostname=hostnames[0].reference)]

    all_new_oois = (
        hostnames
        + addresses
        + v4_addresses
        + ports
        + services
        + ip_services
        + dns_ns_records
        + dns_a_records
        + dns_aaaa_records
        + dns_mx_records
        + sites
    )
    octopoes_api_connector.save_observation(
        Observation(
            method="normalizer_id",
            source=network.reference,
            source_method="manual",
            task_id=uuid.uuid4(),
            valid_time=valid_time,
            result=all_new_oois,
        )
    )

    octopoes_api_connector.save_many_scan_profiles(
        [DeclaredScanProfile(reference=ooi.reference, level=ScanLevel.L2) for ooi in all_new_oois + [network]],
        valid_time,
    )

    # Regarding these queries, we test the following relations:
    #     websites[0] -{hostname}-> hostnames[0]
    #         <-{hostname}- dns_ns_records[0] -{name_server_hostname}-> hostnames[3]
    #         <-{hostname}- dns_aaa_records[0] -> ip_addresses[0]

    # Hostname -> Network
    query = "Hostname.network"
    results = octopoes_api_connector.query(query, valid_time)
    assert len(results) == 10

    # Website -> Hostname -> DNSNSRecord
    query = "Website.hostname.<hostname[is DNSNSRecord]"
    results = octopoes_api_connector.query(query, valid_time)
    assert len(results) == 1

    # Website -> Hostname -> DNSNSRecord -> Hostname -> DNSAAAARecord
    query = "Website.hostname.<hostname[is DNSNSRecord].name_server_hostname.<hostname[is DNSAAAARecord].address"
    results = octopoes_api_connector.query(query, valid_time)
    assert len(results) == 1
    assert str(results[0].address) == "3e4d:64a2:cb49:bd48:a1ba:def3:d15d:9230"

    # Regarding this query, we test the following relations:
    #         -{mail_hostname}-> hostnames[3] <-{hostname}- dns_a_records[0]
    #         -{address}-> v4_addresses[0] <-{address}- ip_ports[1]

    # Hostname -> DNSMXRecord -> Hostname -> DNSARecord -> IPAddress -> IPPort
    query = "Hostname.<hostname[is DNSMXRecord].mail_hostname.<hostname[is DNSARecord].address.<address[is IPPort]"
    results = octopoes_api_connector.query(query, valid_time)
    assert len(results) == 1
    assert str(results[0].port) == "443"

    results = octopoes_api_connector.query(query, valid_time, source=hostnames[0])
    assert len(results) == 0

    results = octopoes_api_connector.query(query, valid_time, source=hostnames[1])
    assert len(results) == 1

    query = "Hostname.<hostname[is DNSNSRecord]"
    assert len(octopoes_api_connector.query(query, valid_time, hostnames[0])) == 1
    assert len(octopoes_api_connector.query(query, valid_time, hostnames[1])) == 1
    assert len(octopoes_api_connector.query(query, valid_time, hostnames[2])) == 1
    assert len(octopoes_api_connector.query(query, valid_time, hostnames[3])) == 0

    result = octopoes_api_connector.query_many(
        query, valid_time, [hostnames[0], hostnames[1], hostnames[2], hostnames[3]]
    )
    assert len(result) == 3
    assert result[0][0] == hostnames[0].reference
    assert result[0][1] == dns_ns_records[0]


def test_no_disappearing_ports(octopoes_api_connector: OctopoesAPIConnector):
    first_valid_time = datetime.now(timezone.utc)
    import time

    network = Network(name="test")
    octopoes_api_connector.save_declaration(Declaration(ooi=network, valid_time=first_valid_time))

    ip = IPAddressV4(network=network.reference, address="10.10.10.10")
    tcp_port = IPPort(address=ip.reference, protocol=Protocol.TCP, port=3306, state=PortState.OPEN)

    octopoes_api_connector.save_observation(
        Observation(
            method="kat_nmap_normalize",
            source=ip.reference,
            source_method="nmap",
            task_id=uuid.uuid4(),
            valid_time=first_valid_time,
            result=[ip, tcp_port],
        )
    )

    octopoes_api_connector.save_many_scan_profiles(
        [DeclaredScanProfile(reference=ooi.reference, level=ScanLevel.L2) for ooi in [ip, tcp_port, network]],
        first_valid_time,
    )
    second_valid_time = datetime.now(timezone.utc)

    time.sleep(2)
    octopoes_api_connector.recalculate_bits()
    time.sleep(2)

    findings = octopoes_api_connector.list_findings({severity for severity in RiskLevelSeverity}, second_valid_time)

    assert findings.items == [
        Finding(
            finding_type=KATFindingType(id="KAT-OPEN-DATABASE-PORT").reference,
            description="Port 3306/tcp is a database port and should not be open.",
            ooi=tcp_port.reference,
        )
    ]

    udp_port = IPPort(address=ip.reference, protocol=Protocol.UDP, port=53, state=PortState.OPEN)

    octopoes_api_connector.save_observation(
        Observation(
            method="kat_nmap_normalize",
            source=ip.reference,
            source_method="nmap-udp",
            task_id=uuid.uuid4(),
            valid_time=second_valid_time,
            result=[ip, udp_port],
        )
    )

    octopoes_api_connector.save_scan_profile(
        DeclaredScanProfile(reference=udp_port.reference, level=ScanLevel.L2), second_valid_time
    )

    assert octopoes_api_connector.get(udp_port.reference, second_valid_time)

    octopoes_api_connector.recalculate_bits()
    time.sleep(2)

    third_valid_time = datetime.now(timezone.utc)

    assert octopoes_api_connector.get(udp_port.reference, third_valid_time)

    findings = octopoes_api_connector.list_findings({severity for severity in RiskLevelSeverity}, third_valid_time)
    assert octopoes_api_connector.get(tcp_port.reference, third_valid_time)

    assert findings.items == [
        Finding(
            finding_type=KATFindingType(id="KAT-OPEN-DATABASE-PORT").reference,
            description="Port 3306/tcp is a database port and should not be open.",
            ooi=tcp_port.reference,
        )
    ]
