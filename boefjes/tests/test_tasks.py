from pathlib import Path

import pytest
import sys
from typing import List
from unittest import TestCase, mock

from boefjes.job_models import (
    BoefjeMeta,
    NormalizerMeta,
    UnsupportedReturnTypeNormalizer,
    InvalidReturnValueNormalizer,
    NormalizerPlainOOI,
)
from boefjes.job_handler import BoefjeHandler, NormalizerHandler
from boefjes.katalogus.local_repository import LocalPluginRepository
from boefjes.katalogus.models import Boefje, Normalizer, Bit, PluginType

from tests.stubs import get_dummy_data
from boefjes.local import LocalBoefjeJobRunner, LocalNormalizerJobRunner


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

    def test_parse_plain_ooi(self):
        plain_ooi = NormalizerPlainOOI(object_type="Network", name="internet")

        NormalizerHandler._parse_ooi(plain_ooi)

    @mock.patch("boefjes.job_handler.get_environment_settings", return_value={})
    @mock.patch("boefjes.job_handler.bytes_api_client")
    @mock.patch("boefjes.job_handler._find_ooi_in_past")
    def test_handle_boefje_with_exception(self, mock_find_ooi_in_past, mock_bytes_api_client, mock_get_env):
        meta = BoefjeMeta(
            id="some-random-job-id",
            boefje={"id": "dummy_boefje_runtime_exception"},
            input_ooi="Network|internet",
            arguments={},
            organization="_dev",
        )

        local_repository = LocalPluginRepository(Path(__file__).parent / "modules")

        with pytest.raises(RuntimeError):  # Bytes still saves exceptions before they are reraised
            BoefjeHandler(LocalBoefjeJobRunner(local_repository), local_repository).handle(meta)

        mock_bytes_api_client.save_boefje_meta.assert_called_once_with(meta)
        mock_bytes_api_client.save_raw.assert_called_once_with(
            "some-random-job-id",
            "Boefje failed",
            {
                "error/boefje",
                "dummy_boefje_runtime_exception",
                "boefje/dummy_boefje_runtime_exception",
                f"boefje/dummy_boefje_runtime_exception-{meta.parameterized_arguments_hash}",
            },
        )

    def test_exception_raised_unsupported_return_type_normalizer(self):
        meta = NormalizerMeta.parse_raw(get_dummy_data("dns-normalize.json"))
        meta.raw_data.boefje_meta.input_ooi = None
        meta.normalizer.id = "dummy_bad_normalizer_return_type"

        local_repository = LocalPluginRepository(Path(__file__).parent / "modules")
        runner = LocalNormalizerJobRunner(local_repository)

        with self.assertRaises(UnsupportedReturnTypeNormalizer):
            runner.run(meta, b"123")

    def test_exception_raised_invalid_return_value(self):
        meta = NormalizerMeta.parse_raw(get_dummy_data("dns-normalize.json"))
        meta.raw_data.boefje_meta.input_ooi = None
        meta.normalizer.id = "dummy_bad_normalizer_dict_structure"

        local_repository = LocalPluginRepository(Path(__file__).parent / "modules")
        runner = LocalNormalizerJobRunner(local_repository)

        with self.assertRaises(InvalidReturnValueNormalizer):
            runner.run(meta, b"123")
