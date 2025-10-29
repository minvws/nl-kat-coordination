import time

from pytest_django.asserts import assertContains, assertNotContains

from objects.management.commands.generate_benchmark_data import generate
from objects.models import (
    DNSAAAARecord,
    DNSARecord,
    DNSNSRecord,
    Finding,
    FindingType,
    Hostname,
    IPAddress,
    IPPort,
    Network,
    Protocol,
    Software,
    XTDBOrganization,
    bulk_insert,
    to_xtdb_dict,
)
from objects.views import FindingListView, NetworkListView
from tasks.tasks import recalculate_scan_levels, sync_ns_scan_levels
from tests.conftest import setup_request


def test_query_hostname(xtdb, organization):
    network = Network.objects.create(name="internet")
    Hostname.objects.create(network=network, name="test.com")
    time.sleep(0.1)

    networks = Network.objects.filter(hostname__name="test.com")
    assert networks.count() == 1
    networks = Network.objects.filter(hostname__name="none.com")
    assert networks.count() == 0

    network.organizations.add(XTDBOrganization.objects.get(pk=organization.pk))
    network.save()
    assert Network.objects.filter(organizations__in=[]).count() == 0
    assert Network.objects.filter(organizations__pk__in=[organization.pk]).count() == 1


def test_recalculate_scan_levels_hostname_ip(xtdb, organization):
    network = Network.objects.create(name="internet")

    h = Hostname.objects.create(network=network, name="test.com", scan_level=2)
    # The A record inherits level 2 from the hostname test.com
    ip = IPAddress.objects.create(network=network, address="0.0.0.0", scan_level=1)
    DNSARecord.objects.create(ip_address=ip, hostname=h)

    # The AAAA record inherits level 2 from the hostname test.com
    ip6 = IPAddress.objects.create(network=network, address="0.0.0.0")
    DNSAAAARecord.objects.create(ip_address=ip6, hostname=h)

    ip2 = IPAddress.objects.create(network=network, address="1.0.0.0")
    DNSARecord.objects.create(ip_address=ip2, hostname=h)

    recalculate_scan_levels()

    ip.refresh_from_db()
    assert ip.scan_level == 2

    ip.scan_level = 3
    ip.save()
    recalculate_scan_levels()

    h.refresh_from_db()
    assert h.scan_level == 3


def test_recalculate_scan_levels_nameserver(xtdb, organization):
    network = Network.objects.create(name="internet")
    h = Hostname.objects.create(network=network, name="test.com", scan_level=2)

    nameserver = Hostname.objects.create(network=network, name="ns.test.com")
    DNSNSRecord.objects.create(name_server=nameserver, hostname=h)

    sync_ns_scan_levels()

    nameserver.refresh_from_db()
    assert nameserver.scan_level == 1


def test_recalculate_scan_levels_does_not_change_declared(xtdb, organization):
    network = Network.objects.create(name="internet")

    h = Hostname.objects.create(network=network, name="test.com", scan_level=2)
    ip = IPAddress.objects.create(network=network, address="0.0.0.0", scan_level=1, declared=True)
    DNSARecord.objects.create(ip_address=ip, hostname=h)
    nameserver = Hostname.objects.create(network=network, name="ns.test.com", scan_level=2, declared=True)
    DNSNSRecord.objects.create(name_server=nameserver, hostname=h)

    recalculate_scan_levels()

    ip.refresh_from_db()
    assert ip.scan_level == 1

    nameserver.refresh_from_db()
    assert nameserver.scan_level == 2


def test_recalculate_scan_levels_creates_new_profiles(xtdb, organization):
    network = Network.objects.create(name="internet")

    h = Hostname.objects.create(network=network, name="test.com", scan_level=2)
    ip = IPAddress.objects.create(network=network, address="0.0.0.0")
    DNSARecord.objects.create(ip_address=ip, hostname=h)

    recalculate_scan_levels()

    ip.refresh_from_db()
    assert ip.scan_level == 2
    assert ip.declared is False

    h.refresh_from_db()
    assert h.scan_level == 2
    assert h.declared is False


def test_network_view_filtered_on_name(rf, superuser_member, xtdb):
    Network.objects.create(name="internet")

    request = setup_request(rf.get("objects:network_list", query_params={"name": "nter"}), superuser_member.user)
    response = NetworkListView.as_view()(request)
    assert response.status_code == 200
    assertContains(response, "internet")
    assertContains(response, "Networks")

    request = setup_request(rf.get("objects:network_list"), superuser_member.user)
    response = NetworkListView.as_view()(request)
    assert response.status_code == 200
    assertContains(response, "internet")

    request = setup_request(rf.get("objects:network_list", query_params={"name": "no"}), superuser_member.user)
    response = NetworkListView.as_view()(request)
    assert response.status_code == 200
    assertNotContains(response, "internet")


def test_findings(rf, superuser_member, xtdb):
    net = Network.objects.create(name="internet")
    host = Hostname.objects.create(name="test.com", network=net)
    finding_type = FindingType.objects.create(code="KAT-TEST-LIST-VIEW", score=3.1)
    Finding.objects.create(hostname=host, finding_type=finding_type)

    request = setup_request(rf.get("objects:finding_list"), superuser_member.user)
    response = FindingListView.as_view()(request)
    assert response.status_code == 200
    assertContains(response, "Severity")
    assertContains(response, "Object")
    assertContains(response, "test.com")
    assertContains(response, "3.1")

    request = setup_request(
        rf.get("objects:finding_list", query_params={"object_search": "mail"}), superuser_member.user
    )
    response = FindingListView.as_view()(request)
    assertNotContains(response, "test.com")

    request = setup_request(
        rf.get("objects:finding_list", query_params={"finding_type__score__gte": 5}), superuser_member.user
    )
    response = FindingListView.as_view()(request)
    assertNotContains(response, "test.com")

    request = setup_request(
        rf.get("objects:finding_list", query_params={"finding_type__score__gte": 3}), superuser_member.user
    )
    response = FindingListView.as_view()(request)
    assertContains(response, "test.com")

    request = setup_request(
        rf.get("objects:finding_list", query_params={"finding_type__code": "KAT-WRONG"}), superuser_member.user
    )
    response = FindingListView.as_view()(request)
    assertNotContains(response, "test.com")

    request = setup_request(
        rf.get("objects:finding_list", query_params={"finding_type__code": "KAT-TEST-LIST-VIEW"}), superuser_member.user
    )
    response = FindingListView.as_view()(request)
    assertContains(response, "test.com")

    request = setup_request(
        rf.get("objects:finding_list", query_params={"object_search": "test"}), superuser_member.user
    )
    response = FindingListView.as_view()(request)
    assertContains(response, "test.com")

    host.delete()
    assert Finding.objects.count() == 0


def test_update_get_or_create(xtdb):
    net = Network.objects.create(name="internet")
    assert Network.objects.count() == 1

    Network.objects.update_or_create(name="internet")
    assert Network.objects.count() == 1

    Network.objects.update_or_create(name="internet")
    assert Network.objects.count() == 1

    other, created = Network.objects.get_or_create(name="internet")
    assert net == other

    other, created = Network.objects.get_or_create(name="test")
    assert net != other


def test_bulk_create(xtdb):
    net = Network(name="internet")
    net2 = Network(name="internet2")
    net3 = Network(name="internet3")
    Network.objects.bulk_create([net, net2, net3])

    assert Network.objects.count() == 3

    nnet = Network(name="internet2")
    nnet2 = Network(name="internet2")
    nnet3 = Network(name="internet4")
    Network.objects.bulk_create([nnet, nnet2, nnet3], unique_fields=["name"])

    assert Network.objects.count() == 6  # Not working in XTDB currently


def test_bulk_insert_networks(xtdb):
    net = Network(name="internet")
    net2 = Network(name="internet2")
    net3 = Network(name="internet3")

    bulk_insert([net, net2, net3])
    assert Network.objects.count() == 3

    net4 = Network(name="internet4")
    net5 = Network(name="internet5")
    net6 = Network(name="internet6")
    host = Hostname(name="test.com", network=net)
    bulk_insert([net4, net5, net6, host])

    assert Network.objects.count() == 6
    assert Hostname.objects.count() == 0


def test_to_dict(xtdb):
    net = Network.objects.create(name="internet")
    host = Hostname.objects.create(name="test.com", network=net)
    ip = IPAddress.objects.create(network=net, address="2001:ab8:d0cb::")
    port = IPPort.objects.create(address=ip, protocol=Protocol.TCP, port=22, tls=False, service="ssh")
    sw = Software.objects.create(name="openssh")
    port.software.add(sw)
    port.save()
    assert to_xtdb_dict(net) == {"name": "internet", "_id": net.id, "declared": False, "scan_level": None}
    assert to_xtdb_dict(host) == {
        "name": "test.com",
        "network_id": net.id,
        "_id": host.id,
        "root": True,
        "declared": False,
        "scan_level": None,
    }
    assert to_xtdb_dict(sw) == {"_id": sw.id, "cpe": None, "name": "openssh", "version": None}


def test_bulk_insert_hostnames(xtdb):
    net = Network.objects.create(name="internet")
    host = Hostname.objects.create(name="test.com", network=net)
    host1 = Hostname.objects.create(name="test1.com", network=net)
    host2 = Hostname.objects.create(name="test2.com", network=net)
    host3 = Hostname.objects.create(name="test3.com", network=net)

    bulk_insert([host, host1, host2, host3])
    assert Hostname.objects.count() == 4


def test_generate_benchmark_data(xtdb):
    objects = generate(10, 1, 1, True)
    for object_t in objects:
        bulk_insert(object_t)

    assert Network.objects.count() == 1
    assert Hostname.objects.count() == 10
    assert IPAddress.objects.count() == 12
    assert DNSARecord.objects.count() == 5
    assert Software.objects.count() == 2
