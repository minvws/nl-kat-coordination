from unittest import TestCase

from pydantic import parse_obj_as

from boefjes.job_handler import serialize_ooi
from boefjes.plugins.kat_website_software.normalize import run
from octopoes.models.types import OOIType
from tests.loading import get_boefje_meta, get_dummy_data, get_normalizer_meta


class WappalizerNormalizerTest(TestCase):
    def test_only_yield_redirected_url_when_redirected(self):
        input_ooi = parse_obj_as(
            OOIType,
            {
                "object_type": "HostnameHTTPURL",
                "network": "Network|internet",
                "scheme": "https",
                "port": 443,
                "path": "/",
                "netloc": "Hostname|internet|web.site",
            },
        )
        boefje_meta = get_boefje_meta(input_ooi=input_ooi.reference)
        boefje_meta.arguments["input"] = serialize_ooi(input_ooi)

        output = [x for x in run(get_normalizer_meta(boefje_meta), get_dummy_data("raw/wappalizer_redirected.json"))]

        self.assertEqual(2, len(output))
        self.assertEqual("URL||https://mid.url/", str(output[0]))
        self.assertEqual("URL||https://redirected.url/", str(output[1]))

    def test_yield_software_when_not_redirected(self):
        input_ooi = parse_obj_as(
            OOIType,
            {
                "object_type": "HostnameHTTPURL",
                "network": "Network|internet",
                "scheme": "https",
                "port": 443,
                "path": "/",
                "netloc": "Hostname|internet|redirected.url",
            },
        )
        boefje_meta = get_boefje_meta(input_ooi=input_ooi.reference)
        boefje_meta.arguments["input"] = serialize_ooi(input_ooi)
        output = [x for x in run(get_normalizer_meta(boefje_meta), get_dummy_data("raw/wappalizer.json"))]

        self.assertEqual(4, len(output))
        self.assertEqual("Software|Hugo|0.104.0|", str(output[0]))
        self.assertEqual("HostnameHTTPURL|https|internet|redirected.url|443|/", str(output[1].ooi))
        self.assertEqual("Software|Hugo|0.104.0|", str(output[1].software))
