from django.db.models import Case, Count, F, When
from djangoql.queryset import apply_search
from djangoql.schema import DjangoQLSchema, IntField

from objects.models import DNSAAAARecord, DNSNSRecord, DNSTXTRecord, Hostname, IPAddress, Network

rules = {
    "ipv6_webservers": {
        "name": "ipv6_webservers",
        "object_type": "Hostname",
        "query": "ns_targets = None and aaaa_records = None",
        "finding_type_code": "KAT-WEBSERVER-NO-IPV6",
    },
    "ipv6_nameservers": {
        "name": "ipv6_nameservers",
        "object_type": "Hostname",
        "query": "ns_targets != None and aaaa_records = None",
        "finding_type_code": "KAT-NAMESERVER-NO-IPV6",
    },
    "two_ipv6_nameservers": {
        "name": "two_ipv6_nameservers",
        "object_type": "Hostname",
        "query": "ns_targets = None and nameservers_with_ipv6_count < 2",
        "finding_type_code": "KAT-NAMESERVER-NO-TWO-IPV6",
    },
    "missing_spf": {
        "name": "missing_spf",
        "object_type": "Hostname",
        "query": 'txt_records.value not startswith "v=spf1"',
        "finding_type_code": "KAT-NO-SPF",
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
                When(ns_records__name_server__aaaa_records__isnull=False, then=F("ns_records__name_server_id")),
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
