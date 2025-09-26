import time

from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import OuterRef, Subquery
from pytest_django.asserts import assertContains, assertNotContains

from objects.models import Hostname, Network, ScanLevel, bulk_insert, to_xtdb_dict
from objects.views import NetworkListView
from tests.conftest import setup_request


def test_query_hostname(xtdb):
    network = Network.objects.create(name="internet")
    Hostname.objects.create(network=network, name="test.com")
    time.sleep(0.1)

    networks = Network.objects.filter(hostname__name="test.com")
    assert networks.count() == 1
    networks = Network.objects.filter(hostname__name="none.com")
    assert networks.count() == 0


def test_query_with_scan_levels(xtdb, organization):
    network = Network.objects.create(name="internet")
    host = Hostname.objects.create(network=network, name="test.com")
    ScanLevel.objects.create(organization=organization.pk, object_type="hostname", object_id=host.id)
    time.sleep(0.1)

    scan_level_query = (
        ScanLevel.objects.filter(object_type="hostname", object_id=OuterRef("id"))
        .values("object_id")
        .annotate(scan_levels=ArrayAgg("scan_level"))
        .values("scan_levels")
    )
    host = Hostname.objects.annotate(scan_levels=Subquery(scan_level_query)).get(pk=host.pk)
    assert host.scan_levels == [0]

    ScanLevel.objects.create(organization=organization.pk, object_type="hostname", object_id=host.id, scan_level=2)
    assert ScanLevel.objects.count() == 2

    host = Hostname.objects.annotate(scan_levels=Subquery(scan_level_query)).get(pk=host.pk)
    assert set(host.scan_levels) == {0, 2}


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

    assert to_xtdb_dict(net) == {"name": "internet", "_id": net.id}
    assert to_xtdb_dict(host) == {"name": "test.com", "network_id": net.id, "_id": host.id}


def test_bulk_insert_hostnames(xtdb):
    net = Network.objects.create(name="internet")
    host = Hostname.objects.create(name="test.com", network=net)
    host1 = Hostname.objects.create(name="test1.com", network=net)
    host2 = Hostname.objects.create(name="test2.com", network=net)
    host3 = Hostname.objects.create(name="test3.com", network=net)

    bulk_insert([host, host1, host2, host3])
    assert Hostname.objects.count() == 4
