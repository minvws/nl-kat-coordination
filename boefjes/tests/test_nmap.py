from unittest import TestCase

from boefjes.job_handler import serialize_ooi
from boefjes.plugins.kat_nmap_tcp.normalize import run
from octopoes.models.ooi.network import IPAddressV4, Network
from tests.loading import get_dummy_data


class NmapTest(TestCase):
    def test_normalizer(self):
        input_ooi = IPAddressV4(network=Network(name="internet").reference, address="134.209.85.72")
        output = list(run(serialize_ooi(input_ooi), get_dummy_data("raw/nmap_mispoes.xml")))
        self.assertEqual(16, len(output))
        for i, out in enumerate(output[:-1]):
            if out.object_type == "IPPort" and output[i + 1].object_type == "Service":
                if out.port == 80:
                    self.assertEqual("http", output[i + 1].name)
                elif out.port == 443:
                    self.assertEqual("https", output[i + 1].name)
                else:
                    self.assertNotEqual("http", output[i + 1].name)
                    self.assertNotEqual("https", output[i + 1].name)
