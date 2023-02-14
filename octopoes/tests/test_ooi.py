import ipaddress
from unittest import TestCase

from octopoes.models import Reference
from tests.mocks.mock_ooi_types import MockNetwork, MockIPAddressV4, MockLabel


class OOITest(TestCase):
    def test_reference_custom_natural_key(self):
        internet = MockNetwork(name="internet")
        ip = MockIPAddressV4(network=internet.reference, address=ipaddress.IPv4Address("1.1.1.1"))
        label = MockLabel(ooi=ip.reference, label_id="LABEL-1000")
        self.assertEqual("MockLabel|MockIPAddressV4|internet|1.1.1.1|LABEL-1000", str(label.reference))

    def test_reference_equality(self):

        internet = MockNetwork(name="internet")
        self.assertEqual(Reference.from_str("MockNetwork|internet"), internet.reference)
