from ipaddress import IPv4Address, IPv6Address
from unittest.mock import MagicMock

from boefjes.plugins.kat_fierce.normalize import run
from octopoes.models import Reference
from octopoes.models.ooi.dns.zone import Hostname, ResolvedHostname
from octopoes.models.ooi.network import IPAddressV4, IPAddressV6, Network
from tests.loading import get_dummy_data


def test_fierce():
    oois = set(run(MagicMock(), get_dummy_data("inputs/fierce-result-example.com.json")))

    expected = {
        ResolvedHostname(
            object_type="ResolvedHostname",
            primary_key="ResolvedHostname|internet|www.example.com|192.0.2.2",
            hostname=Reference("Hostname|internet|www.example.com"),
            address=Reference("IPAddressV4|internet|192.0.2.2"),
        ),
        ResolvedHostname(
            object_type="ResolvedHostname",
            primary_key="ResolvedHostname|internet|subdomain.example.com|192.0.2.3",
            hostname=Reference("Hostname|internet|subdomain.example.com"),
            address=Reference("IPAddressV4|internet|192.0.2.3"),
        ),
        ResolvedHostname(
            object_type="ResolvedHostname",
            primary_key="ResolvedHostname|internet|ipv6.example.com|ff02::1",
            hostname=Reference("Hostname|internet|ipv6.example.com"),
            address=Reference("IPAddressV6|internet|ff02::1"),
        ),
        Hostname(
            object_type="Hostname",
            primary_key="Hostname|internet|example.com",
            network=Reference("Network|internet"),
            name="example.com",
        ),
        Hostname(
            object_type="Hostname",
            primary_key="Hostname|internet|www.example.com",
            registered_domain=Reference("Hostname|internet|example.com"),
            network=Reference("Network|internet"),
            name="www.example.com",
        ),
        Hostname(
            object_type="Hostname",
            primary_key="Hostname|internet|subdomain.example.com",
            registered_domain=Reference("Hostname|internet|example.com"),
            network=Reference("Network|internet"),
            name="subdomain.example.com",
        ),
        Hostname(
            object_type="Hostname",
            primary_key="Hostname|internet|ipv6.example.com",
            registered_domain=Reference("Hostname|internet|example.com"),
            network=Reference("Network|internet"),
            name="ipv6.example.com",
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
        IPAddressV6(
            object_type="IPAddressV6",
            primary_key="IPAddressV6|internet|ff02::1",
            address=IPv6Address("ff02::1"),
            network=Reference("Network|internet"),
        ),
        Network(object_type="Network", primary_key="Network|internet", name="internet"),
    }

    assert oois == expected
