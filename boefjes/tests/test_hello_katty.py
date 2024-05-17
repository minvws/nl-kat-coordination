from unittest import TestCase

from boefjes.job_handler import serialize_ooi
from boefjes.plugins.kat_hello_katty.normalize import run
from octopoes.models.ooi.greeting import Greeting
from octopoes.models.ooi.network import IPAddressV4, Network
from tests.loading import get_dummy_data


class HelloKattyTest(TestCase):
    def test_normalizer(self):
        input_ooi = IPAddressV4(network=Network(name="internet").reference, address="208.84.5.208")
        output = list(run(serialize_ooi(input_ooi), get_dummy_data("raw/hello_katty_raw.json")))
        self.assertEqual(3, len(output))

        for ooi in output:
            self.assertTrue(type(ooi) in [Network, IPAddressV4, Greeting])
