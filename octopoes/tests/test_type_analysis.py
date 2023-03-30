from __future__ import annotations

from unittest import TestCase
from unittest.mock import patch

from octopoes.models import OOI
from octopoes.models.types import (
    get_concrete_types,
    get_abstract_types,
    to_concrete,
    type_by_name,
    get_relations,
    get_collapsed_types,
)
from tests.mocks.mock_ooi_types import (
    MockNetwork,
    MockIPAddress,
    MockIPAddressV4,
    MockIPAddressV6,
    MockIPPort,
    MockDNSCNAMERecord,
    MockResolvedHostname,
    MockHostname,
    ALL_OOI_TYPES,
    MockDNSZone,
)


@patch("octopoes.models.types.ALL_TYPES", ALL_OOI_TYPES)
class TypeSystemTest(TestCase):
    def test_concrete_types(self):
        self.assertSetEqual(
            {
                MockNetwork,
                MockIPAddressV4,
                MockIPAddressV6,
                MockIPPort,
                MockHostname,
                MockResolvedHostname,
                MockDNSCNAMERecord,
                MockDNSZone,
            },
            get_concrete_types(),
        )

    def test_abstract_types(self):
        self.assertSetEqual({OOI, MockIPAddress}, get_abstract_types())

    def test_collapsed_types(self):
        self.assertSetEqual(
            {
                MockIPAddress,
                MockIPPort,
                MockNetwork,
                MockHostname,
                MockResolvedHostname,
                MockDNSCNAMERecord,
                MockDNSZone,
            },
            get_collapsed_types(),
        )

    def test_abstract_to_concrete(self):
        self.assertEqual({MockIPAddressV4, MockIPAddressV6}, to_concrete({MockIPAddress}))

    def test_ooi_to_concrete(self):
        self.assertSetEqual(
            {
                MockNetwork,
                MockIPAddressV4,
                MockIPAddressV6,
                MockIPPort,
                MockHostname,
                MockResolvedHostname,
                MockDNSCNAMERecord,
                MockDNSZone,
            },
            to_concrete({OOI}),
        )

    def test_concrete_to_concrete(self):
        self.assertSetEqual(
            {MockIPAddressV4},
            to_concrete({MockIPAddressV4}),
        )

    def test_type_by_name(self):
        self.assertEqual(MockIPAddressV4, type_by_name("MockIPAddressV4"))

    def test_get_relations(self):
        self.assertEqual({"network": MockNetwork}, get_relations(MockIPAddressV4))

    def test_get_relations_abstract_class(self):
        self.assertEqual({"address": MockIPAddress}, get_relations(MockIPPort))
