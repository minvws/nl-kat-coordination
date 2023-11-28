import os
import uuid
from datetime import datetime
from ipaddress import ip_address
from typing import List

import pytest

from octopoes.api.models import Declaration, Observation
from octopoes.config.settings import XTDBType
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import OOI, DeclaredScanProfile, Reference, ScanLevel
from octopoes.models.ooi.dns.records import DNSAAAARecord, DNSARecord, DNSMXRecord, DNSNSRecord
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.network import IPAddressV4, IPAddressV6, IPPort, Network
from octopoes.models.ooi.service import IPService, Service
from octopoes.models.ooi.web import Website
from octopoes.models.origin import OriginType
from octopoes.repositories.ooi_repository import XTDBOOIRepository

if os.environ.get("CI") != "1":
    pytest.skip("Needs XTDB multinode container.", allow_module_level=True)


XTDBOOIRepository.xtdb_type = XTDBType.XTDB_MULTINODE


def test_bulk_operations(octopoes_api_connector: OctopoesAPIConnector, valid_time: datetime):
    network = Network(name="test")
    octopoes_api_connector.save_declaration(
        Declaration(
            ooi=network,
            valid_time=valid_time,
        )
    )
    hostnames: List[OOI] = [Hostname(network=network.reference, name=f"test{i}") for i in range(10)]
    task_id = uuid.uuid4()

    octopoes_api_connector.save_observation(
        Observation(
            method="normalizer_id",
            source=network.reference,
            task_id=task_id,
            valid_time=valid_time,
            result=hostnames,
        )
    )

    octopoes_api_connector.save_many_scan_profiles(
        [DeclaredScanProfile(reference=ooi.reference, level=ScanLevel.L2) for ooi in hostnames + [network]], valid_time
    )

    assert octopoes_api_connector.list(types={Network}).count == 1
    assert octopoes_api_connector.list(types={Hostname}).count == 10
    assert octopoes_api_connector.list(types={Network, Hostname}).count == 11

    assert len(octopoes_api_connector.list_origins(task_id=uuid.uuid4())) == 0
    origins = octopoes_api_connector.list_origins(task_id=task_id)
    assert len(origins) == 1
    assert origins[0].dict() == {
        "method": "normalizer_id",
        "origin_type": OriginType.OBSERVATION,
        "source": network.reference,
        "result": [hostname.reference for hostname in hostnames],
        "task_id": task_id,
    }

    assert len(octopoes_api_connector.list_origins(result=hostnames[0].reference)) == 1

    # Delete even-numbered test hostnames
    octopoes_api_connector.delete_many([Reference.from_str(f"Hostname|test|test{i}") for i in range(0, 10, 2)])
    assert octopoes_api_connector.list(types={Network, Hostname}).count == 6


def test_query(octopoes_api_connector: OctopoesAPIConnector, valid_time: datetime):
    network = Network(name="test")
    octopoes_api_connector.save_declaration(
        Declaration(
            ooi=network,
            valid_time=valid_time,
        )
    )

    hostnames: List[OOI] = [Hostname(network=network.reference, name=f"test{i}") for i in range(10)]

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
            task_id=uuid.uuid4(),
            valid_time=valid_time,
            result=all_new_oois,
        )
    )

    octopoes_api_connector.save_many_scan_profiles(
        [
            DeclaredScanProfile(
                reference=ooi.reference,
                level=ScanLevel.L2,
            )
            for ooi in all_new_oois + [network]
        ],
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

    results = octopoes_api_connector.query(query, valid_time, source=hostnames[0].reference)
    assert len(results) == 0

    results = octopoes_api_connector.query(query, valid_time, source=hostnames[1].reference)
    assert len(results) == 1
