import json
import time

from objects.models import Hostname, Network


def test_network_api(drf_client, xtdb):
    assert drf_client.get("/api/v1/network/").json() == {"count": 0, "next": None, "previous": None, "results": []}

    net = Network.objects.create(name="internet")
    net2 = Network.objects.create(name="internet2")
    assert drf_client.get("/api/v1/network/?ordering=name").json() == {
        "count": 2,
        "next": None,
        "previous": None,
        "results": [{"id": net.pk, "name": "internet"}, {"id": net2.pk, "name": "internet2"}],
    }

    assert drf_client.get("/api/v1/network/?ordering=-name").json()["results"] == [
        {"id": net2.pk, "name": "internet2"},
        {"id": net.pk, "name": "internet"},
    ]
    network = {"name": "internet3"}
    net3 = drf_client.post("/api/v1/network/", data=json.dumps(network), content_type="application/json").json()

    assert drf_client.get("/api/v1/network/?ordering=-name").json()["results"] == [
        {"id": net3["id"], "name": "internet3"},
        {"id": net2.pk, "name": "internet2"},
        {"id": net.pk, "name": "internet"},
    ]


def test_hostname_api(drf_client, xtdb):
    network = Network.objects.create(name="internet")
    Network.objects.create(name="internet2")
    assert drf_client.get("/api/v1/hostname/").json()["results"] == []

    hn = Hostname.objects.create(network=network, name="test.com")
    assert drf_client.get("/api/v1/hostname/").json()["results"] == [
        {"id": hn.pk, "name": "test.com", "network": network.pk}
    ]

    hostname = {"network": network.pk, "name": "test2.com"}
    hn2 = drf_client.post("/api/v1/hostname/", data=json.dumps(hostname), content_type="application/json").json()
    assert drf_client.get("/api/v1/hostname/?ordering=name").json()["results"] == [
        {"id": hn.pk, "name": "test.com", "network": network.pk},
        {"id": hn2["id"], "name": "test2.com", "network": network.pk},
    ]


def test_bulk_create(drf_client, xtdb):
    n = 50
    networks = [{"name": f"net{i}"} for i in range(n)]
    nets = drf_client.post("/api/v1/network/", data=json.dumps(networks), content_type="application/json").json()
    time.sleep(0.3)
    assert drf_client.get("/api/v1/network/").json()["count"] == n

    hostnames = [{"name": f"host{i}.com", "network": nets[i % 10]["id"]} for i in range(2 * n)]
    drf_client.post("/api/v1/hostname/", data=json.dumps(hostnames), content_type="application/json").json()
    time.sleep(0.3)
    assert drf_client.get("/api/v1/hostname/").json()["count"] == 2 * n
