import time

from django.db.models import Case, Count, F, When
from djangoql.queryset import apply_search

from objects.models import (
    CAATag,
    DNSAAAARecord,
    DNSCAARecord,
    DNSNSRecord,
    DNSTXTRecord,
    Hostname,
    IPAddress,
    IPPort,
    Network,
    Protocol,
)
from plugins.plugins.business_rules import HostnameQLSchema, get_rules


def test_ipv6_query(xtdb):
    network = Network.objects.create(name="test")
    hn = Hostname.objects.create(network=network, name="test.com")
    ns = Hostname.objects.create(network=network, name="ns1.test.com")
    DNSNSRecord.objects.create(hostname=hn, name_server=ns)

    hns = apply_search(Hostname.objects.distinct(), get_rules()["ipv6_webservers"]["query"])
    assert hns.count() == 1
    assert hns.first().name == "test.com"

    ip = IPAddress.objects.create(network=network, address="2001:ab8:d0cb::")
    DNSAAAARecord.objects.create(hostname=hn, ip_address=ip)  # Add DNSAAAARecord to hostname to indicate it has IPV6

    hns = apply_search(Hostname.objects.distinct(), get_rules()["ipv6_webservers"]["query"])
    assert hns.count() == 0


def test_ns_ipv6_query(xtdb):
    network = Network.objects.create(name="test")
    hn = Hostname.objects.create(network=network, name="test.com")
    ns = Hostname.objects.create(network=network, name="ns1.test.com")
    DNSNSRecord.objects.create(hostname=hn, name_server=ns)

    hns = apply_search(Hostname.objects.distinct(), get_rules()["ipv6_nameservers"]["query"])
    assert hns.count() == 1
    assert hns.first().name == "ns1.test.com"

    ip = IPAddress.objects.create(network=network, address="2001:ab8:d0cb::")
    DNSAAAARecord.objects.create(hostname=ns, ip_address=ip)  # Add DNSAAAARecord to nameserver to indicate it has IPV6

    hns = apply_search(Hostname.objects.distinct(), get_rules()["ipv6_nameservers"]["query"])
    assert hns.count() == 0


def test_at_least_two_ipv6_name_servers_query(xtdb):
    network = Network.objects.create(name="test")
    hn = Hostname.objects.create(network=network, name="test.com")
    ip = IPAddress.objects.create(network=network, address="2001:ab8:d0cb::")

    ns1 = Hostname.objects.create(network=network, name="ns1.test.com")
    ns2 = Hostname.objects.create(network=network, name="ns2.test.com")
    ns3 = Hostname.objects.create(network=network, name="ns3.test.com")
    ns4 = Hostname.objects.create(network=network, name="ns4.test.com")
    DNSNSRecord.objects.create(hostname=hn, name_server=ns1)
    DNSNSRecord.objects.create(hostname=hn, name_server=ns2)
    DNSNSRecord.objects.create(hostname=hn, name_server=ns3)
    DNSNSRecord.objects.create(hostname=hn, name_server=ns4)

    queryset = Hostname.objects.annotate(
        nameservers_with_ipv6_count=Count(
            Case(
                When(dnsnsrecord__name_server__dnsaaaarecord__isnull=False, then=F("dnsnsrecord__name_server_id")),
                default=None,
            ),
            distinct=True,
        )
    )

    hns = apply_search(queryset, get_rules()["two_ipv6_nameservers"]["query"], HostnameQLSchema)
    assert hns.count() == 1
    assert hns.first().name == "test.com"

    DNSAAAARecord.objects.create(hostname=ns1, ip_address=ip)

    hns = apply_search(queryset, get_rules()["two_ipv6_nameservers"]["query"], HostnameQLSchema)
    assert hns.count() == 1
    assert hns.first().name == "test.com"

    DNSAAAARecord.objects.create(hostname=ns2, ip_address=ip)

    # Now two nameservers have ipv6
    hns = apply_search(queryset, get_rules()["two_ipv6_nameservers"]["query"], HostnameQLSchema)
    assert hns.count() == 0


def test_missing_spf(xtdb):
    network = Network.objects.create(name="test")
    hn = Hostname.objects.create(network=network, name="test.com")
    time.sleep(0.1)

    assert len(Hostname.objects.raw(get_rules()["missing_spf"]["query"])) == 1
    assert Hostname.objects.raw(get_rules()["missing_spf"]["query"])[0].name == "test.com"

    DNSTXTRecord.objects.create(hostname=hn, value="vspf1")
    assert len(Hostname.objects.raw(get_rules()["missing_spf"]["query"])) == 1

    DNSTXTRecord.objects.create(hostname=hn, value="v=spf1")
    assert len(Hostname.objects.raw(get_rules()["missing_spf"]["query"])) == 0

    DNSTXTRecord.objects.create(hostname=hn, value="random")
    assert len(Hostname.objects.raw(get_rules()["missing_spf"]["query"])) == 0

    DNSTXTRecord.objects.create(hostname=hn, value="v=spf1 number 2")
    assert len(Hostname.objects.raw(get_rules()["missing_spf"]["query"])) == 0


def test_port_classification(xtdb):
    network = Network.objects.create(name="test")
    ip = IPAddress.objects.create(network=network, address="127.0.0.1")

    assert apply_search(IPPort.objects.all(), get_rules()["open_sysadmin_port"]["query"]).count() == 0

    IPPort.objects.create(address=ip, protocol=Protocol.TCP, port=80, tls=False, service="unknown")
    assert apply_search(IPPort.objects.all(), get_rules()["open_sysadmin_port"]["query"]).count() == 0

    IPPort.objects.create(address=ip, protocol=Protocol.TCP, port=21, tls=False, service="unknown")
    assert apply_search(IPPort.objects.all(), get_rules()["open_sysadmin_port"]["query"]).count() == 1

    IPPort.objects.create(address=ip, protocol=Protocol.TCP, port=22, tls=False, service="unknown")
    assert apply_search(IPPort.objects.all(), get_rules()["open_sysadmin_port"]["query"]).count() == 2

    assert apply_search(IPPort.objects.all(), get_rules()["open_database_port"]["query"]).count() == 0

    IPPort.objects.create(address=ip, protocol=Protocol.TCP, port=5432, tls=False, service="unknown")
    assert apply_search(IPPort.objects.all(), get_rules()["open_database_port"]["query"]).count() == 1

    assert apply_search(IPPort.objects.all(), get_rules()["open_remote_desktop_port"]["query"]).count() == 0

    IPPort.objects.create(address=ip, protocol=Protocol.TCP, port=3389, tls=False, service="unknown")
    assert apply_search(IPPort.objects.all(), get_rules()["open_remote_desktop_port"]["query"]).count() == 1

    assert apply_search(IPPort.objects.all(), get_rules()["open_uncommon_port"]["query"]).count() == 0

    IPPort.objects.create(address=ip, protocol=Protocol.UDP, port=53, tls=False, service="unknown")
    assert apply_search(IPPort.objects.all(), get_rules()["open_uncommon_port"]["query"]).count() == 0

    IPPort.objects.create(address=ip, protocol=Protocol.TCP, port=12345, tls=False, service="unknown")
    assert apply_search(IPPort.objects.all(), get_rules()["open_uncommon_port"]["query"]).count() == 1

    assert apply_search(IPPort.objects.all(), get_rules()["open_common_port"]["query"]).count() == 6


def test_missing_caa(xtdb):
    network = Network.objects.create(name="test")
    hn = Hostname.objects.create(network=network, name="test.com")
    hn2 = Hostname.objects.create(network=network, name="test2.com")

    assert apply_search(Hostname.objects.all(), get_rules()["missing_caa"]["query"]).count() == 2

    DNSCAARecord.objects.create(hostname=hn, flags=10, tag=CAATag.ISSUE)
    assert apply_search(Hostname.objects.all(), get_rules()["missing_caa"]["query"]).count() == 1

    DNSCAARecord.objects.create(hostname=hn2, flags=10, tag=CAATag.CONTACTEMAIL)
    assert apply_search(Hostname.objects.all(), get_rules()["missing_caa"]["query"]).count() == 0


def test_missing_dmarc(xtdb):
    network = Network.objects.create(name="test")
    h1 = Hostname.objects.create(network=network, name="test.com")
    h0 = Hostname.objects.create(network=network, name="some.test.com")
    h2 = Hostname.objects.create(network=network, name="test2.com")

    hostnames = Hostname.objects.raw(
        f"""
        SELECT
            h.*
        FROM {Hostname._meta.db_table} h
        LEFT JOIN {Hostname._meta.db_table} root_h ON
            root_h.network_id = h.network_id
                AND root_h.root = true
                AND (h.name = root_h.name OR h.name LIKE '%%.' || root_h.name)
        LEFT JOIN {DNSTXTRecord._meta.db_table} direct_dmarc ON
            direct_dmarc.hostname_id = h._id
                AND direct_dmarc.prefix = '_dmarc'
                AND direct_dmarc.value LIKE 'v=DMARC1%%'
        LEFT JOIN {DNSTXTRecord._meta.db_table} root_dmarc ON
            root_dmarc.hostname_id = root_h._id
                AND root_dmarc.prefix = '_dmarc' AND root_dmarc.value LIKE 'v=DMARC1%%'
        where direct_dmarc._id is null and root_dmarc._id is null
    """  # noqa: S608
    )
    assert {hostname.id for hostname in hostnames} == {h0.pk, h1.pk, h2.pk}

    DNSTXTRecord.objects.create(hostname=h1, value="v=DMARC1; p=none; sp=quarantine;", prefix="_dmarc")

    hostnames._result_cache = None
    assert {hostname.id for hostname in hostnames} == {h2.pk}


def test_domain_owner_verification(xtdb):
    network = Network.objects.create(name="test")
    hn = Hostname.objects.create(network=network, name="test.com")
    hn2 = Hostname.objects.create(network=network, name="test2.com")
    ns1 = Hostname.objects.create(network=network, name="ns1.test.com")
    ns2 = Hostname.objects.create(network=network, name="ns2.test.com")
    DNSNSRecord.objects.create(hostname=hn, name_server=ns1)
    DNSNSRecord.objects.create(hostname=hn, name_server=ns2)

    assert apply_search(Hostname.objects.all(), get_rules()["domain_owner_verification"]["query"]).count() == 0

    pending = Hostname.objects.create(network=network, name="ns1.registrant-verification.ispapi.net")
    DNSNSRecord.objects.create(hostname=hn, name_server=pending)
    assert apply_search(Hostname.objects.all(), get_rules()["domain_owner_verification"]["query"]).count() == 1

    DNSNSRecord.objects.create(hostname=hn2, name_server=pending)
    assert apply_search(Hostname.objects.all(), get_rules()["domain_owner_verification"]["query"]).count() == 2
