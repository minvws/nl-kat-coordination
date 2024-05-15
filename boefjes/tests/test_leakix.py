from unittest import TestCase

from pydantic import parse_obj_as

from boefjes.job_handler import serialize_ooi
from boefjes.plugins.kat_leakix.normalize import run
from octopoes.models.types import OOIType
from tests.loading import get_dummy_data


class LeakIxNormalizerTest(TestCase):
    def test_output(self):
        input_ooi = parse_obj_as(
            OOIType,
            {
                "object_type": "HostnameHTTPURL",
                "network": "Network|internet",
                "scheme": "https",
                "port": 443,
                "path": "/",
                "netloc": "Hostname|internet|example.com",
            },
        )

        output = [x for x in run(serialize_ooi(input_ooi), get_dummy_data("raw/leakix-example.com.json"))]

        self.assertEqual(170, len(output))
        self.assertEqual(get_dummy_data("raw/leakix-example.com-output.txt").decode().strip(), str(output))
