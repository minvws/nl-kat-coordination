from unittest import TestCase

from octopoes.models import Reference
from octopoes.models.ooi.network import IPAddressV4
from octopoes.models.tree import ReferenceNode
from octopoes.repositories.ooi_repository import XTDBReferenceNode

xtdb_sample = {
    "crux.db/id": "IPPort|internet|1.1.1.2|tcp|80",
    "IPPort/address": {
        "crux.db/id": "IPAddressV4|internet|1.1.1.2",
        "IPAddressV4/network": {
            "crux.db/id": "Network|internet",
            "IPAddressV6/_network": [{"crux.db/id": "IPAddressV6|internet|2001:1c00:2303:8f00:21c7:4dc2:5738:28af"}],
        },
    },
}

xtdb_sample_2 = {
    "child_dns_zones": [
        {
            "crux.db/id": "DNSZone|internet|minvws.nl.",
            "hostnames": [{"crux.db/id": "Hostname|internet|minvws.nl."}],
            "name_servers": [
                {"crux.db/id": "Hostname|internet|ns3.ssonet.nl."},
                {"crux.db/id": "Hostname|internet|ns2.ssonet.nl."},
                {"crux.db/id": "Hostname|internet|ns1.ssonet.nl."},
            ],
            "network": {"crux.db/id": "Network|internet"},
            "soa": {"crux.db/id": "Hostname|internet|ns3.ssonet.nl."},
        }
    ],
    "crux.db/id": "DNSZone|internet|nl.",
    "name_servers": [
        {
            "crux.db/id": "Hostname|internet|ns3.dns.nl.",
            "dns_zone": {},
            "network": {"crux.db/id": "Network|internet"},
        },
        {
            "crux.db/id": "Hostname|internet|ns2.dns.nl.",
            "dns_zone": {},
            "network": {"crux.db/id": "Network|internet"},
        },
        {
            "crux.db/id": "Hostname|internet|ns1.dns.nl.",
            "dns_zone": {},
            "dns_zones": [{"crux.db/id": "DNSZone|internet|nl."}],
            "network": {"crux.db/id": "Network|internet"},
        },
    ],
    "network": {
        "crux.db/id": "Network|internet",
        "hostnames": [
            {"crux.db/id": "Hostname|internet|mail.ssonet.nl."},
            {"crux.db/id": "Hostname|internet|mail2.ssonet.nl."},
            {"crux.db/id": "Hostname|internet|minvws.nl."},
            {"crux.db/id": "Hostname|internet|ns1.dns.nl."},
            {"crux.db/id": "Hostname|internet|ns1.ssonet.nl."},
            {"crux.db/id": "Hostname|internet|ns2.dns.nl."},
            {"crux.db/id": "Hostname|internet|ns2.ssonet.nl."},
            {"crux.db/id": "Hostname|internet|ns3.dns.nl."},
            {"crux.db/id": "Hostname|internet|ns3.ssonet.nl."},
        ],
        "ip_v4_addresses": [
            {"crux.db/id": "IPAddressV4|internet|1.1.1.1"},
            {"crux.db/id": "IPAddressV4|internet|147.181.98.150"},
        ],
    },
    "parent": {
        "hostnames": [
            {"crux.db/id": "Hostname|internet|mail.ssonet.nl."},
            {"crux.db/id": "Hostname|internet|mail2.ssonet.nl."},
            {"crux.db/id": "Hostname|internet|ns1.dns.nl."},
            {"crux.db/id": "Hostname|internet|ns1.ssonet.nl."},
            {"crux.db/id": "Hostname|internet|ns2.dns.nl."},
            {"crux.db/id": "Hostname|internet|ns2.ssonet.nl."},
            {"crux.db/id": "Hostname|internet|ns3.dns.nl."},
            {"crux.db/id": "Hostname|internet|ns3.ssonet.nl."},
        ]
    },
    "soa": {
        "crux.db/id": "Hostname|internet|ns1.dns.nl.",
        "dns_zone": {},
        "name_server_of": [{"crux.db/id": "DNSZone|internet|nl."}],
        "network": {"crux.db/id": "Network|internet"},
    },
}


class ReferenceNodeTest(TestCase):
    def test_filter_children(self):

        ref_net = Reference("Network|internet")
        ref_ip = Reference("IPAddressV4|1.1.1.2")
        ref_port = Reference("IPPort|IPPort|internet|1.1.1.2|tcp|80")

        port_node = ReferenceNode(reference=ref_port, children={})
        ip_node = ReferenceNode(reference=ref_ip, children={"ports": [port_node]})
        root_node = ReferenceNode(reference=ref_net, children={"ip_addresses": [ip_node]})

        root_node.filter_children(lambda x: x.reference.class_type == IPAddressV4)

        # Node 2 deep should be have no children
        self.assertDictEqual({}, root_node.children["ip_addresses"][0].children)

    def test_xtdb_reference_node_to_reference_node(self):

        root = XTDBReferenceNode.parse_obj(xtdb_sample)
        reference_node = root.to_reference_node("crux.db/id")
        self.assertEqual(
            "IPAddressV6|internet|2001:1c00:2303:8f00:21c7:4dc2:5738:28af",
            str(
                reference_node.children["IPPort/address"][0]
                .children["IPAddressV4/network"][0]
                .children["IPAddressV6/_network"][0]
                .reference
            ),
        )

    def test_collect_references(self):
        refs = {
            Reference.from_str("IPAddressV6|internet|2001:1c00:2303:8f00:21c7:4dc2:5738:28af"),
            Reference.from_str("IPAddressV4|internet|1.1.1.2"),
            Reference.from_str("Network|internet"),
            Reference.from_str("IPPort|internet|1.1.1.2|tcp|80"),
        }

        root = XTDBReferenceNode.parse_obj(xtdb_sample)
        reference_node = root.to_reference_node("crux.db/id")

        self.assertEqual(refs, reference_node.collect_references())

    def test_xtdb_data_to_reference_node_complext(self):

        root = XTDBReferenceNode.parse_obj(xtdb_sample_2)
        reference_node = root.to_reference_node("crux.db/id")

        self.assertEqual("DNSZone|internet|nl.", str(reference_node.reference))
