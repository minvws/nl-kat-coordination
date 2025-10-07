import time

from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Max, OuterRef, Subquery
from pytest_django.asserts import assertContains, assertNotContains

from objects.models import (
    DNSAAAARecord,
    DNSARecord,
    DNSNSRecord,
    Hostname,
    IPAddress,
    Network,
    ScanLevel,
    bulk_insert,
    to_xtdb_dict,
)
from objects.views import NetworkListView
from tasks.tasks import recalculate_scan_profiles
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
    ScanLevel.objects.create(organization=organization, object_type="hostname", object_id=host.id)
    time.sleep(0.1)

    scan_level_subquery = (
        ScanLevel.objects.filter(object_type="hostname", object_id=OuterRef("id"))
        .values("object_id")
        .order_by()
        .annotate(scan_levels=ArrayAgg("scan_level"))  # collect scan levels in subquery
        .annotate(organizations=ArrayAgg("organization"))  # collect scan levels in subquery
    )
    host = (
        Hostname.objects.annotate(scan_levels=Subquery(scan_level_subquery.values("scan_levels")))
        .annotate(organizations=Subquery(scan_level_subquery.values("organizations")))
        .get(pk=host.pk)
    )
    assert host.scan_levels == [0]
    assert host.organizations == [1]

    ScanLevel.objects.create(organization=organization, object_type="hostname", object_id=host.id, scan_level=2)
    assert ScanLevel.objects.count() == 2

    host = (
        Hostname.objects.annotate(scan_levels=Subquery(scan_level_subquery.values("scan_levels")))
        .annotate(organizations=Subquery(scan_level_subquery.values("organizations")))
        .get(pk=host.pk)
    )
    assert set(host.scan_levels) == {0, 2}
    assert host.organizations == [1, 1]


def test_add_scan_level_filter_to_object_query(xtdb, organization):
    network = Network.objects.create(name="internet")
    host = Hostname.objects.create(network=network, name="test.com")
    sl = ScanLevel.objects.create(organization=organization, object_type="hostname", object_id=host.id)
    time.sleep(0.1)

    subquery = Subquery(
        ScanLevel.objects.filter(object_type="hostname", object_id=OuterRef("id"), organization=organization)
        .values("object_id")
        .annotate(max_scan_level=Max("scan_level"))  # Take the because we need a level at least the plugin.scan_level
        .values("max_scan_level")
    )

    assert Hostname.objects.all().annotate(max_scan_level=subquery).filter(max_scan_level__gte=0).count() == 1
    assert Hostname.objects.all().annotate(max_scan_level=subquery).filter(max_scan_level__gte=1).count() == 0

    sl.scan_level = 2
    sl.save()

    assert Hostname.objects.all().annotate(max_scan_level=subquery).filter(max_scan_level__gte=1).count() == 1
    assert Hostname.objects.all().annotate(max_scan_level=subquery).filter(max_scan_level__gte=2).count() == 1
    assert Hostname.objects.all().annotate(max_scan_level=subquery).filter(max_scan_level__gte=3).count() == 0

    # Also check capitalized
    ScanLevel.objects.create(organization=organization, object_type="Hostname", object_id=host.id, scan_level=3)

    assert Hostname.objects.all().annotate(max_scan_level=subquery).filter(max_scan_level__gte=2).count() == 1
    assert Hostname.objects.all().annotate(max_scan_level=subquery).filter(max_scan_level__gte=3).count() == 1


def test_recalculate_scan_profiles_hostname_ip(xtdb, organization):
    network = Network.objects.create(name="internet")

    h = Hostname.objects.create(network=network, name="test.com")
    ScanLevel.objects.create(organization=organization, object_type="hostname", object_id=h.id, scan_level=2)

    # The A record inherits level 2 from the hostname test.com
    ip = IPAddress.objects.create(network=network, address="0.0.0.0")
    DNSARecord.objects.create(ip_address=ip, hostname=h)
    ipsl = ScanLevel.objects.create(organization=organization, object_type="ipaddress", object_id=ip.id, scan_level=1)

    # The AAAA record inherits level 2 from the hostname test.com
    ip6 = IPAddress.objects.create(network=network, address="0.0.0.0")
    DNSAAAARecord.objects.create(ip_address=ip6, hostname=h)

    ip2 = IPAddress.objects.create(network=network, address="1.0.0.0")
    DNSARecord.objects.create(ip_address=ip2, hostname=h)

    updates = recalculate_scan_profiles()
    assert len(updates) == 3

    ipsl.refresh_from_db()
    assert ipsl.scan_level == 2
    assert ScanLevel.objects.filter(object_id=ip2.id, object_type="ipaddress").count() == 1
    assert ScanLevel.objects.filter(object_id=ip6.id, object_type="ipaddress").count() == 1


def test_recalculate_scan_profiles_nameserver(xtdb, organization):
    network = Network.objects.create(name="internet")
    h = Hostname.objects.create(network=network, name="test.com")
    ScanLevel.objects.create(organization=organization, object_type="hostname", object_id=h.id, scan_level=2)

    nameserver = Hostname.objects.create(network=network, name="ns.test.com")
    nsl = ScanLevel.objects.create(organization=organization, object_type="hostname", object_id=nameserver.id)
    DNSNSRecord.objects.create(name_server=nameserver, hostname=h)

    updates = recalculate_scan_profiles()
    assert len(updates) == 1

    nsl.refresh_from_db()
    assert nsl.scan_level == 1


def test_recalculate_scan_profiles_does_not_change_declared(xtdb, organization):
    network = Network.objects.create(name="internet")

    h = Hostname.objects.create(network=network, name="test.com")
    ScanLevel.objects.create(organization=organization, object_type="hostname", object_id=h.id, scan_level=2)
    ip = IPAddress.objects.create(network=network, address="0.0.0.0")
    DNSARecord.objects.create(ip_address=ip, hostname=h)
    sl = ScanLevel.objects.create(
        organization=organization, object_type="ipaddress", object_id=ip.id, scan_level=1, declared=True
    )
    nameserver = Hostname.objects.create(network=network, name="ns.test.com")
    nsl = ScanLevel.objects.create(
        organization=organization, object_type="ipaddress", object_id=nameserver.id, scan_level=2, declared=True
    )
    DNSNSRecord.objects.create(name_server=nameserver, hostname=h)

    updates = recalculate_scan_profiles()
    assert len(updates) == 0

    sl.refresh_from_db()
    assert sl.scan_level == 1

    nsl.refresh_from_db()
    assert nsl.scan_level == 2


def test_recalculate_scan_profiles_creates_new_profiles(xtdb, organization):
    network = Network.objects.create(name="internet")

    h = Hostname.objects.create(network=network, name="test.com")
    ScanLevel.objects.create(organization=organization, object_type="hostname", object_id=h.id, scan_level=2)
    ip = IPAddress.objects.create(network=network, address="0.0.0.0")
    DNSARecord.objects.create(ip_address=ip, hostname=h)

    updates = recalculate_scan_profiles()
    assert len(updates) == 1

    sl = ScanLevel.objects.filter(object_id=ip.id).first()
    assert sl.scan_level == 2
    assert sl.declared is False

    assert ScanLevel.objects.count() == 2


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
    assert to_xtdb_dict(host) == {"name": "test.com", "network_id": net.id, "_id": host.id, "root": True}


def test_bulk_insert_hostnames(xtdb):
    net = Network.objects.create(name="internet")
    host = Hostname.objects.create(name="test.com", network=net)
    host1 = Hostname.objects.create(name="test1.com", network=net)
    host2 = Hostname.objects.create(name="test2.com", network=net)
    host3 = Hostname.objects.create(name="test3.com", network=net)

    bulk_insert([host, host1, host2, host3])
    assert Hostname.objects.count() == 4
