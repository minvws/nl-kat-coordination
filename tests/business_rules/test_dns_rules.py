from django.db.models import Case, Count, F, When
from djangoql.queryset import apply_search
from djangoql.schema import DjangoQLSchema, IntField

from objects.models import DNSAAAARecord, DNSNSRecord, DNSTXTRecord, Hostname, IPAddress, IPPort, Network, Protocol

SA_TCP_PORTS = [
    21,  # FTP
    22,  # SSH
    23,  # Telnet
    5900,  # VNC
]
DB_TCP_PORTS = [
    1433,  # MS SQL Server
    1434,  # MS SQL Server
    3050,  # Interbase/Firebase
    3306,  # MySQL
    5432,  # PostgreSQL
]
MICROSOFT_RDP_PORTS = [
    3389  # Microsoft Remote Desktop
]
COMMON_TCP_PORTS = [
    25,  # SMTP
    53,  # DNS
    80,  # HTTP
    110,  # POP3
    143,  # IMAP
    443,  # HTTPS
    465,  # SMTPS
    587,  # SMTP (message submmission)
    993,  # IMAPS
    995,  # POP3S
]
ALL_COMMON_TCP = COMMON_TCP_PORTS + SA_TCP_PORTS + DB_TCP_PORTS + MICROSOFT_RDP_PORTS

COMMON_UDP_PORTS = [
    53  # DNS
]

rules = {
    "ipv6_webservers": {
        "name": "ipv6_webservers",
        "object_type": "Hostname",
        "query": "dnsnsrecord_nameserver_set = None and dnsaaaarecord = None",
        "finding_type_code": "KAT-WEBSERVER-NO-IPV6",
    },
    "ipv6_nameservers": {
        "name": "ipv6_nameservers",
        "object_type": "Hostname",
        "query": "dnsnsrecord_nameserver_set != None and dnsaaaarecord = None",
        "finding_type_code": "KAT-NAMESERVER-NO-IPV6",
    },
    "two_ipv6_nameservers": {
        "name": "two_ipv6_nameservers",
        "object_type": "Hostname",
        "query": "dnsnsrecord_nameserver_set = None and nameservers_with_ipv6_count < 2",
        "finding_type_code": "KAT-NAMESERVER-NO-TWO-IPV6",
    },
    "missing_spf": {
        "name": "missing_spf",
        "object_type": "Hostname",
        "query": 'dnstxtrecord.value not startswith "v=spf1"',
        "finding_type_code": "KAT-NO-SPF",
    },
    "open_sysadmin_port": {
        "name": "open_sysadmin_port",
        "object_type": "IPPort",
        "query": f'protocol = "TCP" and port in ({",".join(str(x) for x in SA_TCP_PORTS)})',
        "finding_type_code": "KAT-OPEN-SYSADMIN-PORT",
    },
    "open_database_port": {
        "name": "open_database_port",
        "object_type": "IPPort",
        "query": f'protocol = "TCP" and port in ({",".join(str(x) for x in DB_TCP_PORTS)})',
        "finding_type_code": "KAT-OPEN-DATABASE-PORT",
    },
    "open_remote_desktop_port": {
        "name": "open_remote_desktop_port",
        "object_type": "IPPort",
        "query": f'protocol = "TCP" and port in ({",".join(str(x) for x in MICROSOFT_RDP_PORTS)})',
        "finding_type_code": "KAT-REMOTE-DESKTOP-PORT",
    },
    "open_uncommon_port": {
        "name": "open_uncommon_port",
        "object_type": "IPPort",
        "query": f'(protocol = "TCP" and port not in ({",".join(str(x) for x in ALL_COMMON_TCP)})) '
        f'or (protocol = "UDP" and port not in ({",".join(str(x) for x in COMMON_UDP_PORTS)}))',
        "finding_type_code": "KAT-UNCOMMON-OPEN-PORT",
    },
    "open_common_port": {
        "name": "open_common_port",
        "object_type": "IPPort",
        "query": f'(protocol = "TCP" and port in ({",".join(str(x) for x in ALL_COMMON_TCP)})) '
        f'or (protocol = "UDP" and port in ({",".join(str(x) for x in COMMON_UDP_PORTS)}))',
        "finding_type_code": "KAT-COMMON-OPEN-PORT",
    },
}


class HostnameQLSchema(DjangoQLSchema):
    def get_fields(self, model):
        fields = super().get_fields(model)
        if model == Hostname:
            fields += [IntField(name="nameservers_with_ipv6_count")]
        return fields


def test_ipv6_query(xtdb):
    network = Network.objects.create(name="test")
    hn = Hostname.objects.create(network=network, name="test.com")
    ns = Hostname.objects.create(network=network, name="ns1.test.com")
    DNSNSRecord.objects.create(hostname=hn, name_server=ns)

    hns = apply_search(Hostname.objects.distinct(), rules["ipv6_webservers"]["query"])
    assert hns.count() == 1
    assert hns.first().name == "test.com"

    ip = IPAddress.objects.create(network=network, address="2001:ab8:d0cb::")
    DNSAAAARecord.objects.create(hostname=hn, ip_address=ip)  # Add DNSAAAARecord to hostname to indicate it has IPV6

    hns = apply_search(Hostname.objects.distinct(), rules["ipv6_webservers"]["query"])
    assert hns.count() == 0


def test_ns_ipv6_query(xtdb):
    network = Network.objects.create(name="test")
    hn = Hostname.objects.create(network=network, name="test.com")
    ns = Hostname.objects.create(network=network, name="ns1.test.com")
    DNSNSRecord.objects.create(hostname=hn, name_server=ns)

    hns = apply_search(Hostname.objects.distinct(), rules["ipv6_nameservers"]["query"])
    assert hns.count() == 1
    assert hns.first().name == "ns1.test.com"

    ip = IPAddress.objects.create(network=network, address="2001:ab8:d0cb::")
    DNSAAAARecord.objects.create(hostname=ns, ip_address=ip)  # Add DNSAAAARecord to nameserver to indicate it has IPV6

    hns = apply_search(Hostname.objects.distinct(), rules["ipv6_nameservers"]["query"])
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

    hns = apply_search(queryset, rules["two_ipv6_nameservers"]["query"], HostnameQLSchema)
    assert hns.count() == 1
    assert hns.first().name == "test.com"

    DNSAAAARecord.objects.create(hostname=ns1, ip_address=ip)

    hns = apply_search(queryset, rules["two_ipv6_nameservers"]["query"], HostnameQLSchema)
    assert hns.count() == 1
    assert hns.first().name == "test.com"

    DNSAAAARecord.objects.create(hostname=ns2, ip_address=ip)

    # Now two nameservers have ipv6
    hns = apply_search(queryset, rules["two_ipv6_nameservers"]["query"], HostnameQLSchema)
    assert hns.count() == 0


def test_missing_spf(xtdb):
    network = Network.objects.create(name="test")
    hn = Hostname.objects.create(network=network, name="test.com")

    hns = apply_search(Hostname.objects.all(), rules["missing_spf"]["query"])
    assert hns.count() == 1
    assert hns.first().name == "test.com"

    DNSTXTRecord.objects.create(hostname=hn, value="v=spf1")

    assert apply_search(Hostname.objects.all(), rules["missing_spf"]["query"]).count() == 0

    DNSTXTRecord.objects.create(hostname=hn, value="random")

    assert apply_search(Hostname.objects.all(), rules["missing_spf"]["query"]).count() == 0

    DNSTXTRecord.objects.create(hostname=hn, value="v=spf1 number 2")


def test_port_classification(xtdb):
    network = Network.objects.create(name="test")
    ip = IPAddress.objects.create(network=network, address="127.0.0.1")

    assert apply_search(IPPort.objects.all(), rules["open_sysadmin_port"]["query"]).count() == 0

    IPPort.objects.create(address=ip, protocol=Protocol.TCP, port=80, tls=False, service="unknown")
    assert apply_search(IPPort.objects.all(), rules["open_sysadmin_port"]["query"]).count() == 0

    IPPort.objects.create(address=ip, protocol=Protocol.TCP, port=21, tls=False, service="unknown")
    assert apply_search(IPPort.objects.all(), rules["open_sysadmin_port"]["query"]).count() == 1

    IPPort.objects.create(address=ip, protocol=Protocol.TCP, port=22, tls=False, service="unknown")
    assert apply_search(IPPort.objects.all(), rules["open_sysadmin_port"]["query"]).count() == 2

    assert apply_search(IPPort.objects.all(), rules["open_database_port"]["query"]).count() == 0

    IPPort.objects.create(address=ip, protocol=Protocol.TCP, port=5432, tls=False, service="unknown")
    assert apply_search(IPPort.objects.all(), rules["open_database_port"]["query"]).count() == 1

    assert apply_search(IPPort.objects.all(), rules["open_remote_desktop_port"]["query"]).count() == 0

    IPPort.objects.create(address=ip, protocol=Protocol.TCP, port=3389, tls=False, service="unknown")
    assert apply_search(IPPort.objects.all(), rules["open_remote_desktop_port"]["query"]).count() == 1

    assert apply_search(IPPort.objects.all(), rules["open_uncommon_port"]["query"]).count() == 0

    IPPort.objects.create(address=ip, protocol=Protocol.UDP, port=53, tls=False, service="unknown")
    assert apply_search(IPPort.objects.all(), rules["open_uncommon_port"]["query"]).count() == 0

    IPPort.objects.create(address=ip, protocol=Protocol.TCP, port=12345, tls=False, service="unknown")
    assert apply_search(IPPort.objects.all(), rules["open_uncommon_port"]["query"]).count() == 1

    assert apply_search(IPPort.objects.all(), rules["open_common_port"]["query"]).count() == 6
