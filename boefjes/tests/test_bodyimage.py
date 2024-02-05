import json
from pathlib import Path
from unittest import TestCase, mock
from unittest.mock import MagicMock

from requests.models import CaseInsensitiveDict, Response

from boefjes.job_models import BoefjeMeta, NormalizerMeta
from boefjes.katalogus.local_repository import LocalPluginRepository
from boefjes.local import LocalBoefjeJobRunner, LocalNormalizerJobRunner
from tests.loading import get_dummy_data


class WebsiteAnalysisTest(TestCase):
    maxDiff = None

    @mock.patch("boefjes.plugins.kat_webpage_analysis.main.do_request")
    def test_website_analysis(self, do_request_mock: MagicMock):
        meta = BoefjeMeta.model_validate_json(get_dummy_data("webpage-analysis.json"))
        local_repository = LocalPluginRepository(Path(__file__).parent.parent / "boefjes" / "plugins")

        runner = LocalBoefjeJobRunner(local_repository)

        mock_response = Response()
        mock_response._content = bytes(get_dummy_data("download_body"))
        mock_response.headers = CaseInsensitiveDict(json.loads(get_dummy_data("download_headers.json")))

        do_request_mock.return_value = mock_response

        output = runner.run(meta, {})

        self.assertIn("openkat-http/full", output[0][0])
        self.assertIn("openkat-http/headers", output[1][0])
        self.assertIn("openkat-http/body", output[2][0])

    @mock.patch("boefjes.plugins.kat_webpage_analysis.main.do_request")
    def test_website_analysis_for_image(self, do_request_mock: MagicMock):
        meta = BoefjeMeta.model_validate_json(get_dummy_data("webpage-analysis.json"))
        local_repository = LocalPluginRepository(Path(__file__).parent.parent / "boefjes" / "plugins")

        runner = LocalBoefjeJobRunner(local_repository)

        mock_response = Response()
        mock_response._content = bytes(get_dummy_data("cat_image"))
        mock_response.headers = CaseInsensitiveDict(json.loads(get_dummy_data("download_image_headers.json")))

        do_request_mock.return_value = mock_response

        output = runner.run(meta, {})
        self.assertIn("image/jpeg", output[2][0])

    def test_body_image_normalizer(self):
        meta = NormalizerMeta.model_validate_json(get_dummy_data("bodyimage-normalize.json"))
        local_repository = LocalPluginRepository(Path(__file__).parent.parent / "boefjes" / "plugins")

        runner = LocalNormalizerJobRunner(local_repository)
        output = runner.run(meta, get_dummy_data("cat_image")).observations[0].results

        self.assertEqual(1, len(output))
        self.assertEqual(
            {
                "object_type": "ImageMetadata",
                "primary_key": "ImageMetadata|internet|134.209.85.72|tcp|443|https|internet"
                "|mispo.es|https|internet|mispo.es|443|/",
                "resource": "HTTPResource|internet|134.209.85.72|tcp|443|https|internet"
                "|mispo.es|https|internet|mispo.es|443|/",
                "scan_profile": None,
                "image_info": {
                    "format": "JPEG",
                    "frames": 1,
                    "height": 600,
                    "is_animated": False,
                    "mode": "RGB",
                    "size": (600, 600),
                    "width": 600,
                },
            },
            output[0].dict(),
        )

    def test_body_normalizer(self):
        meta = NormalizerMeta.model_validate_json(get_dummy_data("body-normalize.json"))
        local_repository = LocalPluginRepository(Path(__file__).parent.parent / "boefjes" / "plugins")

        runner = LocalNormalizerJobRunner(local_repository)
        output = runner.run(meta, get_dummy_data("download_body")).observations[0].results

        self.assertEqual(4, len(output))

        output_dicts = sorted([o.dict() for o in output], key=lambda x: x["primary_key"])

        self.assertEqual("URL|internet|http://placekitten.com/600/600", output_dicts[0]["primary_key"])
        self.assertEqual("URL|internet|http://placekitten.com/600/600.webp", output_dicts[1]["primary_key"])
        self.assertEqual("URL|internet|https://mispo.es/600/600", output_dicts[2]["primary_key"])
        self.assertEqual("URL|internet|https://mispo.es/600/600.webp", output_dicts[3]["primary_key"])
