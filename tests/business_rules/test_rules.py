import time

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
from plugins.plugins.business_rules import get_rules


def test_ipv6_query(xtdb):
    network = Network.objects.create(name="test")
    hn = Hostname.objects.create(network=network, name="test.com")
    ns = Hostname.objects.create(network=network, name="ns1.test.com")
    DNSNSRecord.objects.create(hostname=hn, name_server=ns)

    hns = Hostname.objects.raw(get_rules()["ipv6_webservers"]["query"])
    assert len(hns) == 1
    assert hns[0].name == "test.com"

    ip = IPAddress.objects.create(network=network, address="2001:ab8:d0cb::")
    DNSAAAARecord.objects.create(hostname=hn, ip_address=ip)  # Add DNSAAAARecord to hostname to indicate it has IPV6

    hns = Hostname.objects.raw(get_rules()["ipv6_webservers"]["query"])
    assert len(hns) == 0


def test_ns_ipv6_query(xtdb):
    network = Network.objects.create(name="test")
    hn = Hostname.objects.create(network=network, name="test.com")
    ns = Hostname.objects.create(network=network, name="ns1.test.com")
    DNSNSRecord.objects.create(hostname=hn, name_server=ns)

    hns = Hostname.objects.raw(get_rules()["ipv6_nameservers"]["query"])
    assert len(hns) == 1
    assert hns[0].name == "ns1.test.com"

    ip = IPAddress.objects.create(network=network, address="2001:ab8:d0cb::")
    DNSAAAARecord.objects.create(hostname=ns, ip_address=ip)  # Add DNSAAAARecord to nameserver to indicate it has IPV6

    hns = Hostname.objects.raw(get_rules()["ipv6_nameservers"]["query"])
    assert len(hns) == 0


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

    hns = Hostname.objects.raw(get_rules()["two_ipv6_nameservers"]["query"])
    assert len(hns) == 1
    assert hns[0].name == "test.com"

    DNSAAAARecord.objects.create(hostname=ns1, ip_address=ip)

    hns = Hostname.objects.raw(get_rules()["two_ipv6_nameservers"]["query"])
    assert len(hns) == 1
    assert hns[0].name == "test.com"

    DNSAAAARecord.objects.create(hostname=ns2, ip_address=ip)

    # Now two nameservers have ipv6
    hns = Hostname.objects.raw(get_rules()["two_ipv6_nameservers"]["query"])
    assert len(hns) == 0


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
    assert len(IPAddress.objects.raw(get_rules()["open_sysadmin_port"]["query"])) == 0

    ip = IPAddress.objects.create(network=network, address="127.0.0.2")
    IPPort.objects.create(address=ip, protocol=Protocol.TCP, port=80, tls=False, service="unknown")
    assert len(IPAddress.objects.raw(get_rules()["open_sysadmin_port"]["query"])) == 0

    ip = IPAddress.objects.create(network=network, address="127.0.0.3")
    IPPort.objects.create(address=ip, protocol=Protocol.TCP, port=21, tls=False, service="unknown")
    assert len(IPAddress.objects.raw(get_rules()["open_sysadmin_port"]["query"])) == 1

    ip = IPAddress.objects.create(network=network, address="127.0.0.4")
    IPPort.objects.create(address=ip, protocol=Protocol.TCP, port=22, tls=False, service="unknown")
    assert len(IPAddress.objects.raw(get_rules()["open_sysadmin_port"]["query"])) == 2

    assert len(IPAddress.objects.raw(get_rules()["open_database_port"]["query"])) == 0

    ip = IPAddress.objects.create(network=network, address="127.0.0.5")
    IPPort.objects.create(address=ip, protocol=Protocol.TCP, port=5432, tls=False, service="unknown")
    assert len(IPAddress.objects.raw(get_rules()["open_database_port"]["query"])) == 1

    assert len(IPAddress.objects.raw(get_rules()["open_remote_desktop_port"]["query"])) == 0

    ip = IPAddress.objects.create(network=network, address="127.0.0.6")
    IPPort.objects.create(address=ip, protocol=Protocol.TCP, port=3389, tls=False, service="unknown")
    assert len(IPAddress.objects.raw(get_rules()["open_remote_desktop_port"]["query"])) == 1

    assert len(IPAddress.objects.raw(get_rules()["open_uncommon_port"]["query"])) == 0

    ip = IPAddress.objects.create(network=network, address="127.0.0.7")
    IPPort.objects.create(address=ip, protocol=Protocol.UDP, port=53, tls=False, service="unknown")
    assert len(IPAddress.objects.raw(get_rules()["open_uncommon_port"]["query"])) == 0

    ip = IPAddress.objects.create(network=network, address="127.0.0.8")
    IPPort.objects.create(address=ip, protocol=Protocol.TCP, port=12345, tls=False, service="unknown")
    assert len(IPAddress.objects.raw(get_rules()["open_uncommon_port"]["query"])) == 1

    assert len(IPAddress.objects.raw(get_rules()["open_common_port"]["query"])) == 6


def test_missing_caa(xtdb):
    network = Network.objects.create(name="test")
    hn = Hostname.objects.create(network=network, name="test.com")
    hn2 = Hostname.objects.create(network=network, name="test2.com")

    assert len(IPAddress.objects.raw(get_rules()["missing_caa"]["query"])) == 2

    DNSCAARecord.objects.create(hostname=hn, flags=10, tag=CAATag.ISSUE)
    assert len(IPAddress.objects.raw(get_rules()["missing_caa"]["query"])) == 1

    DNSCAARecord.objects.create(hostname=hn2, flags=10, tag=CAATag.CONTACTEMAIL)
    assert len(IPAddress.objects.raw(get_rules()["missing_caa"]["query"])) == 0


def test_missing_dmarc(xtdb):
    network = Network.objects.create(name="test")
    h1 = Hostname.objects.create(network=network, name="test.com")
    h0 = Hostname.objects.create(network=network, name="some.test.com")
    h2 = Hostname.objects.create(network=network, name="test2.com")

    hostnames = Hostname.objects.raw(get_rules()["missing_dmarc"]["query"])
    assert {hostname.id for hostname in hostnames} == {h0.pk, h1.pk, h2.pk}

    DNSTXTRecord.objects.create(hostname=h1, value="v=DMARC1; p=none; sp=quarantine;", prefix="_dmarc")

    hostnames = Hostname.objects.raw(get_rules()["missing_dmarc"]["query"])
    assert {hostname.id for hostname in hostnames} == {h2.pk}


def test_domain_owner_verification(xtdb):
    network = Network.objects.create(name="test")
    hn = Hostname.objects.create(network=network, name="test.com")
    hn2 = Hostname.objects.create(network=network, name="test2.com")
    ns1 = Hostname.objects.create(network=network, name="ns1.test.com")
    ns2 = Hostname.objects.create(network=network, name="ns2.test.com")
    DNSNSRecord.objects.create(hostname=hn, name_server=ns1)
    DNSNSRecord.objects.create(hostname=hn, name_server=ns2)

    assert len(Hostname.objects.raw(get_rules()["domain_owner_verification"]["query"])) == 0

    pending = Hostname.objects.create(network=network, name="ns1.registrant-verification.ispapi.net")
    DNSNSRecord.objects.create(hostname=hn, name_server=pending)

    assert len(Hostname.objects.raw(get_rules()["domain_owner_verification"]["query"])) == 1
    assert Hostname.objects.raw(get_rules()["domain_owner_verification"]["query"])[0].name == "test.com"

    DNSNSRecord.objects.create(hostname=hn2, name_server=pending)
    assert len(Hostname.objects.raw(get_rules()["domain_owner_verification"]["query"])) == 2
    assert hn in list(Hostname.objects.raw(get_rules()["domain_owner_verification"]["query"]))
    assert hn2 in list(Hostname.objects.raw(get_rules()["domain_owner_verification"]["query"]))
