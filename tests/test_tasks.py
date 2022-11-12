from pathlib import Path

import sys
from typing import List
from unittest import TestCase, mock

from boefjes.job_models import BoefjeMeta
from boefjes.job_handler import handle_boefje_job
from boefjes.katalogus.models import Boefje, Normalizer, Bit, PluginType
from boefjes.runner import LocalBoefjeJobRunner

import boefjes.plugins.models


class TaskTest(TestCase):
    def setUp(self) -> None:
        self.boefjes = [
            Boefje(
                id="test-boefje-1",
                repository_id="",
                consumes={"SomeOOI"},
                produces=["test-boef-1", "test/text"],
            ),
            Boefje(
                id="test-boefje-2",
                repository_id="",
                consumes={"SomeOOI"},
                produces=["test-boef-2", "test/text"],
            ),
            Boefje(
                id="test-boefje-3",
                repository_id="",
                consumes={"SomeOOI"},
                produces=["test-boef-3", "test/plain"],
            ),
            Boefje(
                id="test-boefje-4",
                repository_id="",
                consumes={"SomeOOI"},
                produces=["test-boef-4", "test/and-simple"],
            ),
        ]
        self.normalizers = [
            Normalizer(
                id="test-normalizer-1",
                repository_id="",
                consumes=["test-boef-3", "test/text"],
                produces=["SomeOOI", "OtherOOI"],
            ),
            Normalizer(
                id="test-normalizer-2",
                repository_id="",
                consumes=["test/text"],
                produces=["SomeOtherOOI"],
            ),
        ]
        self.bits = [
            Bit(
                id="test-bit-1",
                repository_id="",
                consumes="SomeOOI",
                produces=["SomeOOI"],
                parameters=[],
            ),
            Bit(
                id="test-bit-2",
                repository_id="",
                consumes="SomeOOI",
                produces=["SomeOOI", "SomeOtherOOI"],
                parameters=[],
            ),
        ]
        self.plugins: List[PluginType] = self.boefjes + self.normalizers + self.bits
        sys.path.append(str(Path(__file__).parent))

    def _get_boefje_meta(self):
        return BoefjeMeta(
            id="c188ef6b-b756-4cb0-9cb2-0db776e3cce3",
            boefje={"id": "test-boefje-1", "version": "9"},
            input_ooi="Hostname|internet|example.com",
            arguments={},
            organization="_dev",
        ).copy()

    @mock.patch("boefjes.runner.get_environment_settings", return_value={})
    @mock.patch("boefjes.job_handler.bytes_api_client")
    def test_handle_boefje_with_exception(
        self, mock_bytes_api_client, mock_get_environment_settings
    ):
        meta = BoefjeMeta(
            id="some-random-job-id",
            boefje={"id": "dummy-with-exception"},
            input_ooi="Network|internet",
            arguments={},
            organization="_dev",
        )
        boefje = boefjes.plugins.models.BoefjeResource(
            Path(__file__).parent / "modules/dummy_boefje_runtime_exception",
            "modules.dummy_boefje_runtime_exception",
            "",
        )

        handle_boefje_job(meta, LocalBoefjeJobRunner(meta, boefje, {}))

        mock_bytes_api_client.save_boefje_meta.assert_called_once_with(meta)
        mock_bytes_api_client.save_raw.assert_called_once_with(
            "some-random-job-id",
            "dummy error",
            {
                "error/boefje",
                "dummy-with-exception",
                "boefje/dummy-with-exception",
                f"boefje/dummy-with-exception-{meta.parameterized_arguments_hash}",
            },
        )
