from pathlib import Path
from unittest import TestCase

from boefjes.katalogus.local_repository import LocalPluginRepository
from boefjes.local import LocalNormalizerJobRunner
from boefjes.job_models import NormalizerMeta
from tests.stubs import get_dummy_data


class DnsTest(TestCase):
    maxDiff = None

    def test_body_image_normalizer(self):
        meta = NormalizerMeta.parse_raw(get_dummy_data("bodyimage-normalize.json"))
        local_repository = LocalPluginRepository(Path(__file__).parent.parent / "boefjes" / "plugins")

        runner = LocalNormalizerJobRunner(local_repository)
        output = runner.run(meta, get_dummy_data("cat_image"))

        self.assertEqual(1, len(output))
        self.assertEqual({
            "object_type": "ImageMetadata",
            "primary_key": "ImageMetadata|internet|134.209.85.72|tcp|443|https|internet|mispo.es|https|internet|mispo.es|443|/",
            "resource": "HTTPResource|internet|134.209.85.72|tcp|443|https|internet|mispo.es|https|internet|mispo.es|443|/",
            "scan_profile": None,
            "image_info": {
                "format": "JPEG",
                "frames": 1,
                "height": 600,
                "is_animated": False,
                "mode": "RGB",
                "size": (600, 600),
                "width": 600
            },
        }, output[0].dict())

    def test_body_normalizer(self):
        meta = NormalizerMeta.parse_raw(get_dummy_data("body-normalize.json"))
        local_repository = LocalPluginRepository(Path(__file__).parent.parent / "boefjes" / "plugins")

        runner = LocalNormalizerJobRunner(local_repository)
        output = runner.run(meta, get_dummy_data("download_body"))

        self.assertEqual(4, len(output))
