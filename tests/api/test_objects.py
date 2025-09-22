import time

from objects.models import Finding, FindingType, Hostname, IPAddress, IPPort, Network


def test_finding_api(drf_client, xtdb):
    ft = FindingType.objects.create(code="TEST", score=5)
    net = Network.objects.create(name="internet")
    f = Finding.objects.create(finding_type=ft, object_type="Network", object_id=net.id)

    assert drf_client.get("/api/v1/objects/finding/").json() == {
        "count": 1,
        "next": None,
        "previous": None,
        "results": [
            {"id": f.pk, "object_id": net.id, "object_type": "Network", "organization": None, "finding_type": ft.code}
        ],
    }

    hn = Hostname.objects.create(network=net, name="test.com")
    drf_client.post(
        "/api/v1/objects/finding/",
        json={"finding_type_code": "TEST", "object_type": "Hostname", "object_code": hn.name},
    )
    assert drf_client.get("/api/v1/objects/finding/").json()["count"] == 2

    res = drf_client.post(
        "/api/v1/objects/finding/",
        json=[
            {"finding_type_code": "TEST", "object_type": "Network", "object_code": net.name},
            {"finding_type_code": "TEST2", "object_type": "Network", "object_code": net.name},
            {"finding_type_code": "TEST3", "object_type": "Network", "object_code": net.name},
        ],
    )
    assert res.status_code == 201

    res = drf_client.get("/api/v1/objects/findingtype/?code=TEST2")
    test2_id = res.json()["results"][0]["id"]
    res = drf_client.patch(f"/api/v1/objects/findingtype/{test2_id}/", json={"code": "TEST2", "score": 6.0})

    assert res.status_code == 200

    assert drf_client.get("/api/v1/objects/finding/").json()["count"] == 5
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


def test_generic_api_saves_related_objects(drf_client, xtdb):
    Network.objects.create(name="internet")

    ips = [{"network": "internet", "address": "127.0.0.1"}, {"network": "internet", "address": "127.0.0.2"}]
    ports = [{"address": "127.0.0.1", "protocol": "TCP", "port": 80, "service": "http"}]

    drf_client.post("/api/v1/objects/", json={"ipaddress": ips, "ipport": ports})

    assert IPAddress.objects.count() == 2
    assert IPPort.objects.count() == 0  # TODO: fix


def test_bulk_create(drf_client, xtdb):
    n = 50
    networks = [{"name": f"net{i}"} for i in range(n)]
    nets = drf_client.post("/api/v1/objects/network/", json=networks).json()
    time.sleep(0.3)
    assert drf_client.get("/api/v1/objects/network/").json()["count"] == n

    hostnames = [{"name": f"host{i}.com", "network": nets[i % 10]["name"]} for i in range(2 * n)]
    drf_client.post("/api/v1/objects/hostname/", json=hostnames).json()
    time.sleep(0.3)
    assert drf_client.get("/api/v1/objects/hostname/").json()["count"] == 2 * n
