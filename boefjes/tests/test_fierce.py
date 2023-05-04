from ipaddress import IPv4Address
from unittest.mock import MagicMock

from boefjes.plugins.kat_fierce.normalize import run
from octopoes.models import Reference
from octopoes.models.ooi.dns.records import DNSARecord
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.network import IPAddressV4, Network
from tests.stubs import get_dummy_data


def test_fierce():
    oois = set(run(MagicMock(), get_dummy_data("inputs/fierce-result-example.com.json")))

    expected = {
        DNSARecord(
            object_type="DNSARecord",
            primary_key="DNSARecord|internet|subdomain.example.com|192.0.2.3",
            hostname=Reference("Hostname|internet|subdomain.example.com"),
            dns_record_type="A",
            value="192.0.2.3",
            address=Reference("IPAddressV4|internet|192.0.2.3"),
        ),
        DNSARecord(
            object_type="DNSARecord",
            primary_key="DNSARecord|internet|www.example.com|192.0.2.2",
            hostname=Reference("Hostname|internet|www.example.com"),
            dns_record_type="A",
            value="192.0.2.2",
            address=Reference("IPAddressV4|internet|192.0.2.2"),
        ),
        Hostname(
            object_type="Hostname",
            primary_key="Hostname|internet|www.example.com",
            network=Reference("Network|internet"),
            name="www.example.com",
        ),
        Hostname(
            object_type="Hostname",
            primary_key="Hostname|internet|subdomain.example.com",
            network=Reference("Network|internet"),
            name="subdomain.example.com",
        ),
        IPAddressV4(
            object_type="IPAddressV4",
            primary_key="IPAddressV4|internet|192.0.2.3",
            address=IPv4Address("192.0.2.3"),
            network=Reference("Network|internet"),
        ),
        IPAddressV4(
            object_type="IPAddressV4",
            primary_key="IPAddressV4|internet|192.0.2.2",
            address=IPv4Address("192.0.2.2"),
            network=Reference("Network|internet"),
        ),
        Network(object_type="Network", primary_key="Network|internet", name="internet"),
    }

    assert oois == expected
