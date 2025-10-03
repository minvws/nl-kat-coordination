import time
from collections import defaultdict

from objects.models import (
    DNSAAAARecord,
    DNSARecord,
    DNSCNAMERecord,
    DNSNSRecord,
    Finding,
    FindingType,
    Hostname,
    IPAddress,
    IPPort,
    Network,
)


def test_finding_api(drf_client, xtdb, organization):
    ft = FindingType.objects.create(code="TEST", score=5)
    net = Network.objects.create(name="internet")
    f = Finding.objects.create(finding_type=ft, organization=organization, object_type="network", object_id=net.id)

    assert drf_client.get("/api/v1/objects/finding/").json() == {
        "count": 1,
        "next": None,
        "previous": None,
        "results": [
            {
                "id": f.pk,
                "object_id": net.id,
                "object_type": "network",
                "organization": organization.pk,
                "finding_type": ft.code,
            }
        ],
    }

    hn = Hostname.objects.create(network=net, name="test.com")
    res = drf_client.post(
        "/api/v1/objects/finding/",
        json={
            "finding_type_code": "TEST",
            "object_type": "hostname",
            "organization": organization.pk,
            "object_code": hn.name,
        },
    )
    assert res.status_code == 201
    assert drf_client.get("/api/v1/objects/finding/").json()["count"] == 2

    res = drf_client.post(
        "/api/v1/objects/finding/",
        json=[
            {
                "finding_type_code": "TEST",
                "object_type": "network",
                "organization": organization.pk,
                "object_code": net.name,
            },
            {
                "finding_type_code": "TEST2",
                "object_type": "network",
                "organization": organization.pk,
                "object_code": net.name,
            },
            {
                "finding_type_code": "TEST3",
                "object_type": "network",
                "organization": organization.pk,
                "object_code": net.name,
            },
        ],
    )
    assert res.status_code == 201

    res = drf_client.get("/api/v1/objects/findingtype/?code=TEST2")
    test2_id = res.json()["results"][0]["id"]
    res = drf_client.patch(f"/api/v1/objects/findingtype/{test2_id}/", json={"code": "TEST2", "score": 6.0})

    assert res.status_code == 200

    assert drf_client.get("/api/v1/objects/finding/").json()["count"] == 4
    assert drf_client.get("/api/v1/objects/findingtype/").json()["count"] == 3
    test2 = drf_client.get("/api/v1/objects/findingtype/?code=TEST2").json()
    assert test2["count"] == 1
    assert test2["results"][0]["score"] == 6.0


def test_network_api(drf_client, xtdb):
    assert drf_client.get("/api/v1/objects/network/").json() == {
        "count": 0,
        "next": None,
        "previous": None,
        "results": [],
    }

    net = Network.objects.create(name="internet")
    net2 = Network.objects.create(name="internet2")
    assert drf_client.get("/api/v1/objects/network/?ordering=name").json() == {
        "count": 2,
        "next": None,
        "previous": None,
        "results": [{"id": net.pk, "name": "internet"}, {"id": net2.pk, "name": "internet2"}],
    }

    assert drf_client.get("/api/v1/objects/network/?ordering=-name").json()["results"] == [
        {"id": net2.pk, "name": "internet2"},
        {"id": net.pk, "name": "internet"},
    ]
    network = {"name": "internet3"}
    net3 = drf_client.post("/api/v1/objects/network/", json=network).json()

    assert drf_client.get("/api/v1/objects/network/?ordering=-name").json()["results"] == [
        {"id": net3["id"], "name": "internet3"},
        {"id": net2.pk, "name": "internet2"},
        {"id": net.pk, "name": "internet"},
    ]


def test_hostname_api(drf_client, xtdb):
    network = Network.objects.create(name="internet")
    Network.objects.create(name="internet2")
    assert drf_client.get("/api/v1/objects/hostname/").json()["results"] == []

    hn = Hostname.objects.create(network=network, name="test.com")
    assert drf_client.get("/api/v1/objects/hostname/").json()["results"] == [
        {"id": hn.pk, "name": "test.com", "network_id": network.pk}
    ]

    hostname = {"network": "internet", "name": "test2.com"}
    hn2 = drf_client.post("/api/v1/objects/hostname/", json=hostname).json()
    assert drf_client.get("/api/v1/objects/hostname/?ordering=name").json()["results"] == [
        {"id": hn.pk, "name": "test.com", "network_id": network.pk},
        {"id": hn2["id"], "name": "test2.com", "network_id": network.pk},
    ]

    response = drf_client.post("/api/v1/objects/hostname/", json={"name": "test.com"})
    assert response.status_code == 400


def test_ip_api(drf_client, xtdb):
    net = Network.objects.create(name="internet")

    ip = {"network": "internet", "address": "127.0.0.1"}
    ip_res = drf_client.post("/api/v1/objects/ipaddress/", json=ip).json()
    assert drf_client.get("/api/v1/objects/ipaddress/").json()["results"] == [
        {"id": ip_res["id"], "network_id": net.pk, "address": "127.0.0.1"}
    ]

    ipport = {"address": ip_res["id"], "protocol": "TCP", "port": 80, "service": "http"}
    port_res = drf_client.post("/api/v1/objects/ipport/", json=ipport).json()
    assert drf_client.get("/api/v1/objects/ipport/").json()["results"] == [ipport | {"id": port_res["id"], "tls": None}]


def test_generic_api_saves_unrelated_objects(drf_client, xtdb):
    Network.objects.create(name="internet")

    ips = [{"network": "internet", "address": "127.0.0.1"}, {"network": "internet", "address": "127.0.0.2"}]
    hns = [{"network": "internet", "name": "test.com"}, {"network": "internet", "name": "test2.com"}]

    res = drf_client.post("/api/v1/objects/", json={"ipaddress": ips, "hostname": hns})

    assert "ipaddress" in res.json()
    assert "hostname" in res.json()

    assert IPAddress.objects.count() == 2
    assert Hostname.objects.count() == 2


def test_generic_api_saves_unrelated_objects_even_if_some_exist(drf_client, xtdb):
    network = Network.objects.create(name="internet")
    Hostname.objects.create(network=network, name="test.com")

    ips = [{"network": "internet", "address": "127.0.0.1"}, {"network": "internet", "address": "127.0.0.2"}]
    hns = [{"network": "internet", "name": "test.com"}, {"network": "internet", "name": "test2.com"}]

    res = drf_client.post("/api/v1/objects/", json={"ipaddress": ips, "hostname": hns})

    assert "ipaddress" in res.json()
    assert "hostname" in res.json()

    assert IPAddress.objects.count() == 2
    assert Hostname.objects.count() == 2


def test_generic_api_saves_related_objects(drf_client, xtdb):
    Network.objects.create(name="internet")

    ips = [{"network": "internet", "address": "127.0.0.1"}, {"network": "internet", "address": "127.0.0.2"}]
    ports = [{"address": "127.0.0.1", "protocol": "TCP", "port": 80, "service": "http"}]

    drf_client.post("/api/v1/objects/", json={"ipaddress": ips, "ipport": ports})

    assert IPAddress.objects.count() == 2
    assert IPPort.objects.count() == 0  # TODO: fix


def test_bulk_create(drf_client, xtdb):
    n = 25
    networks = [{"name": f"net{i}"} for i in range(n)]
    nets = drf_client.post("/api/v1/objects/network/", json=networks).json()
    time.sleep(0.3)
    assert drf_client.get("/api/v1/objects/network/").json()["count"] == n

    hostnames = [{"name": f"host{i}.com", "network": nets[i % 10]["name"]} for i in range(2 * n)]
    drf_client.post("/api/v1/objects/hostname/", json=hostnames).json()
    time.sleep(0.3)
    assert drf_client.get("/api/v1/objects/hostname/").json()["count"] == 2 * n


def test_dns_records_are_not_duplicated(drf_client, xtdb):
    results_grouped = defaultdict(list)
    results = [
        {"object_type": "ipaddress", "network": "internet", "address": "127.0.0.1"},
        {"object_type": "hostname", "network": "internet", "name": "b.nl"},
        {"object_type": "hostname", "network": "internet", "name": "ns3.a.ns"},
        {"object_type": "hostname", "network": "internet", "name": "ns1.a.ns"},
        {"object_type": "hostname", "network": "internet", "name": "ns2.a.ns"},
        {"object_type": "DNSNSRecord", "name_server": "ns3.a.ns", "hostname": "b.nl", "value": "ns3.a.ns.", "ttl": 1},
        {"object_type": "DNSNSRecord", "name_server": "ns1.a.ns", "hostname": "b.nl", "value": "ns1.a.ns.", "ttl": 1},
        {"object_type": "DNSNSRecord", "name_server": "ns2.a.ns", "hostname": "b.nl", "value": "ns2.a.ns.", "ttl": 1},
        {"object_type": "DNSARecord", "ip_address": "127.0.0.1", "hostname": "b.nl", "value": "127.0.0.1", "ttl": 1},
    ]

    for result in results:
        results_grouped[result.pop("object_type").lower()].append(result)

    hostnames_and_ips = {"hostname": results_grouped.pop("hostname"), "ipaddress": results_grouped.pop("ipaddress")}
    response = drf_client.post("/api/v1/objects/", json=hostnames_and_ips).json()
    by_name = {h["name"]: h["id"] for h in response["hostname"]}
    by_address = {ip["address"]: ip["id"] for ip in response["ipaddress"]}

    for object_path, objects in results_grouped.items():
        for obj in objects:
            if "hostname" in obj:
                obj["hostname"] = by_name[obj["hostname"]]
            if "mail_server" in obj:
                obj["mail_server"] = by_name[obj["mail_server"]]
            if "name_server" in obj:
                obj["name_server"] = by_name[obj["name_server"]]
            if "target" in obj:
                obj["target"] = by_name[obj["target"]]

            if "ip_address" in obj:
                obj["ip_address"] = by_address[obj["ip_address"]]

    drf_client.post("/api/v1/objects/", json=results_grouped)
    time.sleep(0.1)

    assert IPAddress.objects.count() == 1
    assert Hostname.objects.count() == 4
    assert DNSARecord.objects.count() == 1
    assert DNSAAAARecord.objects.count() == 0
    assert DNSNSRecord.objects.count() == 3
    assert DNSCNAMERecord.objects.count() == 0

    drf_client.post("/api/v1/objects/", json=hostnames_and_ips).json()
    drf_client.post("/api/v1/objects/", json=results_grouped)
    time.sleep(0.1)

    assert IPAddress.objects.count() == 1
    assert Hostname.objects.count() == 4
    assert DNSARecord.objects.count() == 1
    assert DNSAAAARecord.objects.count() == 0
    assert DNSNSRecord.objects.count() == 3
    assert DNSCNAMERecord.objects.count() == 0
