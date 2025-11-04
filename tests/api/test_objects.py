from collections import defaultdict
from urllib.parse import quote

from objects.models import (
    DNSAAAARecord,
    DNSARecord,
    DNSCNAMERecord,
    DNSNSRecord,
    DNSTXTRecord,
    Finding,
    FindingType,
    Hostname,
    IPAddress,
    IPPort,
    Network,
    Software,
    XTDBOrganization,
)


def test_finding_api(drf_client, xtdb, organization):
    ft = FindingType.objects.create(code="TEST", score=5)
    net = Network.objects.create(name="internet")
    hn = Hostname.objects.create(network=net, name="test.com")
    f = Finding.objects.create(finding_type=ft, hostname=hn)

    response = drf_client.get("/api/v1/objects/finding/").json()
    assert response["count"] == 1
    assert len(response["results"]) == 1
    assert response["results"][0]["id"] == f.pk
    assert response["results"][0]["finding_type"] == ft.code
    assert response["results"][0]["organizations"] == []

    f.organizations.add(XTDBOrganization.objects.get(pk=organization.pk))

    response = drf_client.get("/api/v1/objects/finding/").json()
    assert response["count"] == 1
    assert response["results"][0]["organizations"] == [organization.pk]

    res = drf_client.post("/api/v1/objects/finding/", json={"finding_type_code": "TEST2", "hostname": hn.name})
    assert res.status_code == 201
    assert drf_client.get("/api/v1/objects/finding/").json()["count"] == 2

    # Create IP address finding
    ip = IPAddress.objects.create(network=net, address="127.0.0.1")
    res = drf_client.post(
        "/api/v1/objects/finding/",
        json=[
            {"finding_type_code": "TEST", "ipaddress": ip.address},
            {"finding_type_code": "TEST2", "hostname": hn.name},
            {"finding_type_code": "TEST3", "hostname": hn.name},
        ],
    )
    assert res.status_code == 201

    res = drf_client.get("/api/v1/objects/findingtype/?code=TEST2")
    assert res.status_code == 200
    test2_code = res.json()["results"][0]["code"]
    res = drf_client.patch(f"/api/v1/objects/findingtype/{test2_code}/", json={"code": "TEST2", "score": 6.0})

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

    Network.objects.create(name="internet")
    Network.objects.create(name="internet2")
    assert drf_client.get("/api/v1/objects/network/?ordering=name").json() == {
        "count": 2,
        "next": None,
        "previous": None,
        "results": [
            {"name": "internet", "declared": False, "scan_level": None, "organizations": []},
            {"name": "internet2", "declared": False, "scan_level": None, "organizations": []},
        ],
    }

    assert drf_client.get("/api/v1/objects/network/?ordering=-name").json()["results"] == [
        {"name": "internet2", "declared": False, "scan_level": None, "organizations": []},
        {"name": "internet", "declared": False, "scan_level": None, "organizations": []},
    ]
    network = {"name": "internet3"}
    drf_client.post("/api/v1/objects/network/", json=network).json()

    assert drf_client.get("/api/v1/objects/network/?ordering=-name").json()["results"] == [
        {"name": "internet3", "declared": False, "scan_level": None, "organizations": []},
        {"name": "internet2", "declared": False, "scan_level": None, "organizations": []},
        {"name": "internet", "declared": False, "scan_level": None, "organizations": []},
    ]


def test_hostname_api(drf_client, xtdb):
    network = Network.objects.create(name="internet")
    Network.objects.create(name="internet2")
    assert drf_client.get("/api/v1/objects/hostname/").json()["results"] == []

    hn = Hostname.objects.create(network=network, name="test.com")
    assert drf_client.get("/api/v1/objects/hostname/").json()["results"] == [
        {
            "id": hn.pk,
            "name": "test.com",
            "dns_records": [],
            "network_id": network.pk,
            "root": True,
            "declared": False,
            "scan_level": None,
            "organizations": [],
        }
    ]

    hostname = {"network": "internet", "name": "test2.com"}
    hn2 = drf_client.post("/api/v1/objects/hostname/", json=hostname).json()
    txt = DNSTXTRecord.objects.create(hostname=hn, value="v=spf1")
    assert drf_client.get("/api/v1/objects/hostname/?ordering=name").json()["results"] == [
        {
            "id": hn.pk,
            "name": "test.com",
            "dns_records": [{"hostname": hn.pk, "id": txt.pk, "prefix": "", "ttl": None, "value": "v=spf1"}],
            "network_id": network.pk,
            "root": True,
            "declared": False,
            "scan_level": None,
            "organizations": [],
        },
        {
            "id": hn2["id"],
            "name": "test2.com",
            "dns_records": [],
            "network_id": network.pk,
            "root": True,
            "declared": False,
            "scan_level": None,
            "organizations": [],
        },
    ]

    response = drf_client.post("/api/v1/objects/hostname/", json={"name": "test.com"})
    assert response.status_code == 400


def test_ip_api(drf_client, xtdb):
    net = Network.objects.create(name="internet")

    ip = {"network": "internet", "address": "127.0.0.1"}
    response = drf_client.post("/api/v1/objects/ipaddress/", json=ip)
    assert response.status_code == 201

    ip_res = response.json()
    assert drf_client.get("/api/v1/objects/ipaddress/").json()["results"] == [
        {
            "id": ip_res["id"],
            "network_id": net.pk,
            "address": "127.0.0.1",
            "declared": False,
            "scan_level": None,
            "organizations": [],
        }
    ]

    ipport = {"address": ip_res["address"], "protocol": "TCP", "port": 80, "service": "http"}
    port_res = drf_client.post("/api/v1/objects/ipport/", json=ipport).json()
    assert drf_client.get("/api/v1/objects/ipport/").json()["results"] == [
        {
            "id": port_res["id"],
            "address_id": ip_res["id"],
            "tls": None,
            "port": 80,
            "service": "http",
            "protocol": "TCP",
            "software": [],
        }
    ]


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

    response = drf_client.post("/api/v1/objects/", json={"ipaddress": ips, "ipport": ports})
    assert response.status_code == 201

    assert IPAddress.objects.count() == 2
    assert IPPort.objects.count() == 1

    data = {
        "ipaddress": [{"address": "134.209.85.72", "network": "internet"}],
        "ipport": [
            {
                "address": "127.0.0.1",
                "protocol": "TCP",
                "port": 80,
                "service": "mysql",
                "software": [{"name": "mysql", "version": "0.1"}],
            }
        ],
    }
    response = drf_client.post("/api/v1/objects/", json=data)
    assert response.status_code == 201

    assert IPPort.objects.count() == 1
    assert IPPort.objects.first().software.count() == 1
    assert Software.objects.count() == 1

    data = {
        "ipaddress": [{"address": "134.209.85.72", "network": "internet"}],
        "ipport": [
            {
                "address": "127.0.0.1",
                "protocol": "TCP",
                "port": 80,
                "service": "mysql",
                "software": [{"name": "mongodb", "version": "0.2"}],
            }
        ],
    }

    response = drf_client.post("/api/v1/objects/", json=data)
    assert response.status_code == 201

    assert IPPort.objects.count() == 1
    assert IPPort.objects.first().software.count() == 2
    assert Software.objects.count() == 2

    response = drf_client.post("/api/v1/objects/", json=data)
    assert response.status_code == 201
    assert IPPort.objects.count() == 1
    assert IPPort.objects.first().software.count() == 2
    assert Software.objects.count() == 2


def test_bulk_create(drf_client, xtdb):
    n = 20
    networks = [{"name": f"net{i}"} for i in range(n)]
    nets = drf_client.post("/api/v1/objects/network/", json=networks).json()
    assert drf_client.get("/api/v1/objects/network/").json()["count"] == n

    hostnames = [{"name": f"host{i}.com", "network": nets[i % 10]["name"]} for i in range(2 * n)]
    drf_client.post("/api/v1/objects/hostname/", json=hostnames).json()
    assert drf_client.get("/api/v1/objects/hostname/").json()["count"] == 2 * n


def test_dns_records_are_not_duplicated(drf_client, xtdb, settings):
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

    response = drf_client.post("/api/v1/objects/", json=results_grouped)
    assert response.status_code == 201

    assert IPAddress.objects.count() == 1
    assert Hostname.objects.count() == 4
    assert DNSARecord.objects.count() == 1
    assert DNSAAAARecord.objects.count() == 0
    assert DNSNSRecord.objects.count() == 3
    assert DNSCNAMERecord.objects.count() == 0

    drf_client.post("/api/v1/objects/", json=hostnames_and_ips).json()
    drf_client.post("/api/v1/objects/", json=results_grouped)

    assert IPAddress.objects.count() == 1
    assert Hostname.objects.count() == 4
    assert DNSARecord.objects.count() == 1
    assert DNSAAAARecord.objects.count() == 0
    assert DNSNSRecord.objects.count() == 3
    assert DNSCNAMERecord.objects.count() == 0


def test_hostname_delete_dns_records_endpoint_validation(drf_client, xtdb):
    network = Network.objects.create(name="internet")
    hostname = Hostname.objects.create(network=network, name="example.com")

    response = drf_client.delete(f"/api/v1/objects/hostname/{hostname.pk}/dnsrecord/")
    assert response.status_code == 400
    assert "error" in response.json()

    response = drf_client.delete(f"/api/v1/objects/hostname/{hostname.pk}/dnsrecord/", json={"record_ids": []})
    assert response.status_code == 400
    assert "error" in response.json()

    response = drf_client.delete(
        f"/api/v1/objects/hostname/{hostname.pk}/dnsrecord/", json={"record_ids": "not-a-list"}
    )
    assert response.status_code == 400
    assert "error" in response.json()

    response = drf_client.delete(f"/api/v1/objects/hostname/{hostname.pk}/dnsrecord/", json={"record_ids": [99999]})
    assert response.status_code == 200
    data = response.json()
    assert "deleted" in data
    assert data["deleted"] == 0


def test_ipport_delete_api(drf_client, xtdb):
    network = Network.objects.create(name="internet")
    ip_address = IPAddress.objects.create(network=network, address="192.0.2.1")
    ipport = IPPort.objects.create(address=ip_address, protocol="TCP", port=80, service="http")

    assert IPPort.objects.filter(pk=ipport.pk).exists()
    response = drf_client.delete(f"/api/v1/objects/ipport/{quote(ipport.pk)}/")

    assert response.status_code == 204  # No Content is the standard DRF delete response
    assert not IPPort.objects.filter(pk=ipport.pk).exists()


def test_ipport_bulk_delete_multiple(drf_client, xtdb):
    network = Network.objects.create(name="internet")
    ip1 = IPAddress.objects.create(network=network, address="192.0.2.1")
    ip2 = IPAddress.objects.create(network=network, address="192.0.2.2")
    ip3 = IPAddress.objects.create(network=network, address="192.0.2.3")

    port1 = IPPort.objects.create(address=ip1, protocol="TCP", port=80, service="http")
    port2 = IPPort.objects.create(address=ip2, protocol="TCP", port=443, service="https")
    port3 = IPPort.objects.create(address=ip3, protocol="TCP", port=22, service="ssh")
    port4 = IPPort.objects.create(address=ip1, protocol="UDP", port=53, service="dns")

    port1_id = port1.pk
    port2_id = port2.pk
    port3_id = port3.pk
    port4_id = port4.pk

    assert IPPort.objects.filter(pk=port1_id).exists()
    assert IPPort.objects.filter(pk=port2_id).exists()
    assert IPPort.objects.filter(pk=port3_id).exists()
    assert IPPort.objects.filter(pk=port4_id).exists()

    response = drf_client.delete(f"/api/v1/objects/ipport/?id={port1_id}&id={port2_id}&id={port3_id}")

    assert response.status_code == 200
    data = response.json()
    assert "deleted" in data
    assert data["deleted"] == 3

    assert not IPPort.objects.filter(pk=port1_id).exists()
    assert not IPPort.objects.filter(pk=port2_id).exists()
    assert not IPPort.objects.filter(pk=port3_id).exists()

    assert IPPort.objects.filter(pk=port4_id).exists()


def test_hostname_delete_dns_records_integration(drf_client, xtdb):
    objects_data = {
        "ipaddress": [
            {"network": "internet", "address": "192.0.2.1"},
            {"network": "internet", "address": "2001:db8::1"},
            {"network": "internet", "address": "192.0.2.2"},
        ],
        "hostname": [
            {"network": "internet", "name": "example.com"},
            {"network": "internet", "name": "ns1.example.com"},
            {"network": "internet", "name": "other.com"},
        ],
    }
    response = drf_client.post("/api/v1/objects/", json=objects_data)
    assert response.status_code == 201
    created = response.json()

    hostname_id = created["hostname"][0]["id"]
    ns_hostname_id = created["hostname"][1]["id"]
    other_hostname_id = created["hostname"][2]["id"]
    ip_id = created["ipaddress"][0]["id"]
    ip6_id = created["ipaddress"][1]["id"]
    other_ip_id = created["ipaddress"][2]["id"]

    dns_records = {
        "dnsarecord": [{"hostname": hostname_id, "ip_address": ip_id, "ttl": 3600}],
        "dnsaaaarecord": [{"hostname": hostname_id, "ip_address": ip6_id, "ttl": 3600}],
        "dnstxtrecord": [{"hostname": hostname_id, "value": "v=spf1 -all", "ttl": 3600}],
        "dnsnsrecord": [{"hostname": hostname_id, "name_server": ns_hostname_id, "ttl": 3600}],
    }
    response = drf_client.post("/api/v1/objects/", json=dns_records)
    assert response.status_code == 201
    created_dns = response.json()

    # Test new dns records field in hostname api responses
    hn = drf_client.get(f"/api/v1/objects/hostname/?name={quote('example.com')}").json()
    dns_records = hn["results"][0]["dns_records"]
    assert len(dns_records) == 4

    ids = [
        created_dns["dnsarecord"][0]["id"],
        created_dns["dnsaaaarecord"][0]["id"],
        created_dns["dnstxtrecord"][0]["id"],
        created_dns["dnsnsrecord"][0]["id"],
    ]
    assert ids == [dns["id"] for dns in dns_records]

    other_dns_records = {
        "dnsarecord": [{"hostname": other_hostname_id, "ip_address": other_ip_id, "ttl": 7200}],
        "dnstxtrecord": [{"hostname": other_hostname_id, "value": "v=spf1 include:_spf.google.com ~all", "ttl": 7200}],
    }
    response = drf_client.post("/api/v1/objects/", json=other_dns_records)
    assert response.status_code == 201

    initial_a_records = DNSARecord.objects.count()
    initial_txt_records = DNSTXTRecord.objects.count()
    assert initial_a_records >= 2  # At least 2 A records (one for each hostname)
    assert initial_txt_records >= 2  # At least 2 TXT records

    other_hostname_a_records = DNSARecord.objects.filter(hostname_id=other_hostname_id).count()
    other_hostname_txt_records = DNSTXTRecord.objects.filter(hostname_id=other_hostname_id).count()
    assert other_hostname_a_records >= 1
    assert other_hostname_txt_records >= 1

    response = drf_client.delete(
        f"/api/v1/objects/hostname/{hostname_id}/dnsrecord/?record_id={'&record_id='.join([str(rec) for rec in ids])}"
    )

    assert response.status_code == 200
    data = response.json()
    assert "deleted" in data
    assert data["deleted"] == 4

    assert DNSARecord.objects.filter(hostname_id=other_hostname_id).count() == other_hostname_a_records
    assert DNSTXTRecord.objects.filter(hostname_id=other_hostname_id).count() == other_hostname_txt_records
