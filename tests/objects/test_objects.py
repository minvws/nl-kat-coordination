import time

from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Max, OuterRef, Subquery
from pytest_django.asserts import assertContains, assertNotContains

from objects.models import (
    DNSARecord,
    DNSCNAMERecord,
    DNSMXRecord,
    DNSNSRecord,
    Hostname,
    IPAddress,
    IPPort,
    Network,
    Protocol,
    ScanLevel,
    bulk_insert,
    to_xtdb_dict,
)
from objects.views import HostnameDetailView, NetworkListView
from openkat.models import Organization
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


def test_recalculate_scan_profiles(xtdb, organization):
    network = Network.objects.create(name="internet")

    h = Hostname.objects.create(network=network, name="test.com")
    ScanLevel.objects.create(organization=organization, object_type="hostname", object_id=h.id, scan_level=2)

    nameserver = Hostname.objects.create(network=network, name="ns.test.com")
    nsl = ScanLevel.objects.create(organization=organization, object_type="hostname", object_id=nameserver.id)

    mailserver = Hostname.objects.create(network=network, name="mail.test.com")
    ScanLevel.objects.create(organization=organization, object_type="hostname", object_id=mailserver.id, scan_level=1)

    # The A record inherits level 2 from the hostname test.com
    ip = IPAddress.objects.create(network=network, address="0.0.0.0")
    A = DNSARecord.objects.create(ip_address=ip, hostname=h)
    sl = ScanLevel.objects.create(organization=organization, object_type="dnsarecord", object_id=A.id, scan_level=1)

    port = IPPort.objects.create(address=ip, protocol=Protocol.TCP, port=80, tls=False, service="unknown")
    port_sl = ScanLevel.objects.create(organization=organization, object_type="ipport", object_id=port.id, scan_level=1)

    NS = DNSNSRecord.objects.create(name_server=nameserver, hostname=h)

    # The MX record inherits level 1 from the hostname mail.test.com through the mail_server field
    MX = DNSMXRecord.objects.create(mail_server=mailserver, hostname=h)
    mxsl = ScanLevel.objects.create(organization=organization, object_type="dnsmxrecord", object_id=MX.id)

    recalculate_scan_profiles()

    sl.refresh_from_db()
    assert sl.scan_level == 2

    nsl.refresh_from_db()  # The DNSNSRecord has no scan level yet, so nothing happens. Something to implement still.
    assert nsl.scan_level == 0

    mxsl.refresh_from_db()
    assert mxsl.scan_level == 1

    ScanLevel.objects.create(organization=organization, object_type="dnsnsrecord", object_id=NS.id, scan_level=2)
    recalculate_scan_profiles()

    nsl.refresh_from_db()  # Now we do see the effect
    assert nsl.scan_level == 1

    port_sl.refresh_from_db()
    assert port_sl.scan_level == 1

    ScanLevel.objects.create(organization=organization, object_type="ipaddress", object_id=ip.id, scan_level=4)
    recalculate_scan_profiles()

    port_sl.refresh_from_db()
    assert port_sl.scan_level == 4


def test_recalculate_scan_profiles_does_not_change_declared(xtdb, organization):
    network = Network.objects.create(name="internet")

    h = Hostname.objects.create(network=network, name="test.com")
    ScanLevel.objects.create(organization=organization, object_type="hostname", object_id=h.id, scan_level=2)
    ip = IPAddress.objects.create(network=network, address="0.0.0.0")
    A = DNSARecord.objects.create(ip_address=ip, hostname=h)
    sl = ScanLevel.objects.create(
        organization=organization, object_type="dnsarecord", object_id=A.id, scan_level=1, declared=True
    )

    recalculate_scan_profiles()

    sl.refresh_from_db()
    assert sl.scan_level == 1


def test_recalculate_scan_profiles_creates_new_profiles(xtdb, organization):
    network = Network.objects.create(name="internet")

    h = Hostname.objects.create(network=network, name="test.com")
    ScanLevel.objects.create(organization=organization, object_type="hostname", object_id=h.id, scan_level=2)
    ip = IPAddress.objects.create(network=network, address="0.0.0.0")
    A = DNSARecord.objects.create(ip_address=ip, hostname=h)

    recalculate_scan_profiles()

    sl = ScanLevel.objects.filter(object_id=A.id).first()
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


def test_hostname_detail_view_shows_dns_record_max_scan_levels(rf, superuser_member, xtdb, organization):
    # Create network and hostnames
    net = Network.objects.create(name="internet")
    hostname = Hostname.objects.create(name="example.com", network=net)
    Hostname.objects.create(name="target.example.com", network=net)
    mailserver = Hostname.objects.create(name="mail.example.com", network=net)
    nameserver = Hostname.objects.create(name="ns.example.com", network=net)

    # Create IP addresses
    ip1 = IPAddress.objects.create(network=net, address="1.2.3.4")
    IPAddress.objects.create(network=net, address="5.6.7.8")

    # Create DNS records
    a_record = DNSARecord.objects.create(hostname=hostname, ip_address=ip1, ttl=300)
    Hostname.objects.get(name="target.example.com")
    mx_record = DNSMXRecord.objects.create(hostname=hostname, mail_server=mailserver, preference=10, ttl=300)
    ns_record = DNSNSRecord.objects.create(hostname=hostname, name_server=nameserver, ttl=300)

    # Create scan levels for the DNS records themselves
    ScanLevel.objects.create(organization=organization, object_type="dnsarecord", object_id=a_record.id, scan_level=2)
    ScanLevel.objects.create(organization=organization, object_type="dnsmxrecord", object_id=mx_record.id, scan_level=1)
    ScanLevel.objects.create(organization=organization, object_type="dnsnsrecord", object_id=ns_record.id, scan_level=4)

    time.sleep(0.1)

    # Make request to hostname detail view
    request = setup_request(rf.get(f"/objects/hostname/{hostname.pk}/"), superuser_member.user)
    response = HostnameDetailView.as_view()(request, pk=hostname.pk)

    # Check that the context contains annotated DNS records
    assert "dnsarecord_set" in response.context_data
    assert "dnsmxrecord_set" in response.context_data
    assert "dnsnsrecord_set" in response.context_data

    # Verify A record has correct max scan level
    a_records = list(response.context_data["dnsarecord_set"])
    assert len(a_records) == 1
    assert a_records[0].max_scan_level == 2

    # Verify MX record has correct max scan level
    mx_records = list(response.context_data["dnsmxrecord_set"])
    assert len(mx_records) == 1
    assert mx_records[0].max_scan_level == 1

    # Verify NS record has correct max scan level
    ns_records = list(response.context_data["dnsnsrecord_set"])
    assert len(ns_records) == 1
    assert ns_records[0].max_scan_level == 4


def test_hostname_detail_view_filters_scan_levels_by_organization(rf, superuser_member, xtdb, organization):
    org2 = Organization.objects.create(name="Test Org 2", code="test-org-2")

    net = Network.objects.create(name="internet")
    hostname = Hostname.objects.create(name="example.com", network=net)
    ip1 = IPAddress.objects.create(network=net, address="1.2.3.4")

    a_record = DNSARecord.objects.create(hostname=hostname, ip_address=ip1, ttl=300)

    ScanLevel.objects.create(organization=organization, object_type="dnsarecord", object_id=a_record.id, scan_level=2)
    ScanLevel.objects.create(organization=org2, object_type="dnsarecord", object_id=a_record.id, scan_level=4)

    time.sleep(0.1)

    request = setup_request(rf.get(f"/objects/hostname/{hostname.pk}/"), superuser_member.user)
    response = HostnameDetailView.as_view()(request, pk=hostname.pk)
    a_records = list(response.context_data["dnsarecord_set"])
    assert len(a_records) == 1
    assert a_records[0].max_scan_level == 4  # Max of 2 and 4

    request = setup_request(
        rf.get(f"/objects/hostname/{hostname.pk}/?organization={organization.code}"), superuser_member.user
    )
    response = HostnameDetailView.as_view()(request, pk=hostname.pk)
    a_records = list(response.context_data["dnsarecord_set"])
    assert len(a_records) == 1
    assert a_records[0].max_scan_level == 2  # Only org1's scan level

    request = setup_request(rf.get(f"/objects/hostname/{hostname.pk}/?organization={org2.code}"), superuser_member.user)
    response = HostnameDetailView.as_view()(request, pk=hostname.pk)
    a_records = list(response.context_data["dnsarecord_set"])
    assert len(a_records) == 1
    assert a_records[0].max_scan_level == 4  # Only org2's scan level


def test_hostname_detail_view_shows_reverse_dns_record_scan_levels(rf, superuser_member, xtdb, organization):
    net = Network.objects.create(name="internet")
    hostname = Hostname.objects.create(name="example.com", network=net)
    source_hostname = Hostname.objects.create(name="source.example.com", network=net)

    cname_record = DNSCNAMERecord.objects.create(hostname=source_hostname, target=hostname, ttl=300)
    mx_record = DNSMXRecord.objects.create(hostname=source_hostname, mail_server=hostname, preference=10, ttl=300)
    ns_record = DNSNSRecord.objects.create(hostname=source_hostname, name_server=hostname, ttl=300)

    ScanLevel.objects.create(
        organization=organization, object_type="dnscnamerecord", object_id=cname_record.id, scan_level=3
    )
    ScanLevel.objects.create(organization=organization, object_type="dnsmxrecord", object_id=mx_record.id, scan_level=2)
    ScanLevel.objects.create(organization=organization, object_type="dnsnsrecord", object_id=ns_record.id, scan_level=1)

    time.sleep(0.1)

    # Make request to hostname detail view
    request = setup_request(rf.get(f"/objects/hostname/{hostname.pk}/"), superuser_member.user)
    response = HostnameDetailView.as_view()(request, pk=hostname.pk)

    # Check reverse DNS records
    assert "dnscnamerecord_target_set" in response.context_data
    assert "dnsmxrecord_mailserver" in response.context_data
    assert "dnsnsrecord_nameserver" in response.context_data

    # Verify CNAME target record has correct scan level
    cname_targets = list(response.context_data["dnscnamerecord_target_set"])
    assert len(cname_targets) == 1
    assert cname_targets[0].max_scan_level == 3

    # Verify MX mailserver record has correct scan level
    mx_mailservers = list(response.context_data["dnsmxrecord_mailserver"])
    assert len(mx_mailservers) == 1
    assert mx_mailservers[0].max_scan_level == 2

    # Verify NS nameserver record has correct scan level
    ns_nameservers = list(response.context_data["dnsnsrecord_nameserver"])
    assert len(ns_nameservers) == 1
    assert ns_nameservers[0].max_scan_level == 1
