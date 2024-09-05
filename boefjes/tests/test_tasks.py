import ast
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest import TestCase, mock
from uuid import UUID

import pytest

from boefjes.job_handler import BoefjeHandler
from boefjes.job_models import BoefjeMeta, InvalidReturnValueNormalizer, NormalizerMeta
from boefjes.local import LocalBoefjeJobRunner, LocalNormalizerJobRunner
from boefjes.local_repository import LocalPluginRepository
from boefjes.models import Bit, Boefje, Normalizer, PluginType
from boefjes.runtime_interfaces import JobRuntimeError
from tests.loading import get_dummy_data


class TaskTest(TestCase):
    def setUp(self) -> None:
        self.boefjes = [
            Boefje(
                id="test-boefje-1",
                name="test-boefje-1",
                consumes={"SomeOOI"},
                produces=["test-boef-1", "test/text"],
            ),
            Boefje(
                id="test-boefje-2",
                name="test-boefje-2",
                consumes={"SomeOOI"},
                produces=["test-boef-2", "test/text"],
            ),
            Boefje(
                id="test-boefje-3",
                name="test-boefje-3",
                consumes={"SomeOOI"},
                produces=["test-boef-3", "test/plain"],
            ),
            Boefje(
                id="test-boefje-4",
                name="test-boefje-4",
                consumes={"SomeOOI"},
                produces=["test-boef-4", "test/and-simple"],
            ),
        ]
        self.normalizers = [
            Normalizer(
                id="test-normalizer-1",
                name="test-normalizer-1",
                consumes=["test-boef-3", "test/text"],
                produces=["SomeOOI", "OtherOOI"],
            ),
            Normalizer(
                id="test-normalizer-2",
                name="test-normalizer-2",
                consumes=["test/text"],
                produces=["SomeOtherOOI"],
            ),
        ]
        self.bits = [
            Bit(
                id="test-bit-1",
                name="test-bit-1",
                consumes="SomeOOI",
                produces=["SomeOOI"],
                parameters=[],
            ),
            Bit(
                id="test-bit-2",
                name="test-bit-2",
                consumes="SomeOOI",
                produces=["SomeOOI", "SomeOtherOOI"],
                parameters=[],
            ),
        ]
        self.plugins: list[PluginType] = self.boefjes + self.normalizers + self.bits
        sys.path.append(str(Path(__file__).parent))

    def _get_boefje_meta(self):
        return BoefjeMeta(
            id="c188ef6b-b756-4cb0-9cb2-0db776e3cce3",
            boefje={"id": "test-boefje-1", "version": "9"},
            input_ooi="Hostname|internet|example.com",
            arguments={},
            organization="_dev",
        ).copy()

    def test_parse_normalizer_meta_to_json(self):
        meta = NormalizerMeta.model_validate_json(get_dummy_data("snyk-normalizer.json"))
        meta.started_at = datetime(10, 10, 10, 10, tzinfo=timezone.utc)
        meta.ended_at = datetime(10, 10, 10, 12, tzinfo=timezone.utc)

        assert "0010-10-10T10:00:00Z" in meta.model_dump_json()
        assert "0010-10-10T12:00:00Z" in meta.model_dump_json()

    @mock.patch("boefjes.job_handler.get_environment_settings", return_value={})
    @mock.patch("boefjes.job_handler.bytes_api_client")
    @mock.patch("boefjes.job_handler.get_octopoes_api_connector")
    def test_handle_boefje_with_exception(self, mock_get_octopoes_api_connector, mock_bytes_api_client, mock_get_env):
        meta = BoefjeMeta(
            id="0dca59db-b339-47c4-bcc9-896fc18e2386",
            boefje={"id": "dummy_boefje_runtime_exception"},
            input_ooi="Network|internet",
            arguments={},
            organization="_dev",
        )

        local_repository = LocalPluginRepository(Path(__file__).parent / "modules")

        with pytest.raises(RuntimeError):  # Bytes still saves exceptions before they are reraised
            BoefjeHandler(LocalBoefjeJobRunner(local_repository), local_repository, mock_bytes_api_client).handle(meta)

        mock_bytes_api_client.save_boefje_meta.assert_called_once_with(meta)
        mock_bytes_api_client.save_raw.assert_called_once()
        raw_call_args = mock_bytes_api_client.save_raw.call_args

        assert raw_call_args[0][0] == UUID("0dca59db-b339-47c4-bcc9-896fc18e2386")
        assert "Traceback (most recent call last)" in raw_call_args[0][1]
        assert "JobRuntimeError: Boefje failed" in raw_call_args[0][1]
        assert raw_call_args[0][2] == {
            "error/boefje",
            "boefje/dummy_boefje_runtime_exception",
        }

    def test_exception_raised_unsupported_return_type_normalizer(self):
        meta = NormalizerMeta.model_validate_json(get_dummy_data("dns-normalize.json"))
        meta.raw_data.boefje_meta.input_ooi = None
        meta.normalizer.id = "dummy_bad_normalizer_return_type"

        local_repository = LocalPluginRepository(Path(__file__).parent / "modules")
        runner = LocalNormalizerJobRunner(local_repository)

        with self.assertRaises(InvalidReturnValueNormalizer):
            runner.run(meta, b"123")

    def test_exception_raised_invalid_return_value(self):
        meta = NormalizerMeta.model_validate_json(get_dummy_data("dns-normalize.json"))
        meta.raw_data.boefje_meta.input_ooi = None
        meta.normalizer.id = "dummy_bad_normalizer_dict_structure"

        local_repository = LocalPluginRepository(Path(__file__).parent / "modules")
        runner = LocalNormalizerJobRunner(local_repository)

        with self.assertRaises(InvalidReturnValueNormalizer):
            runner.run(meta, b"123")

    def test_cleared_boefje_env(self) -> None:
        """This test checks if un-containerized (local) boefjes can only access their explicitly set env vars"""

        arguments = {"ARG1": "value1", "ARG2": "value2"}

        meta = BoefjeMeta(
            id="b49cd6f5-4d92-4a13-9d21-232993826cd9",
            boefje={"id": "dummy_boefje_environment"},
            input_ooi="Network|internet",
            arguments=arguments,
            organization="_dev",
        )

        local_repository = LocalPluginRepository(Path(__file__).parent / "modules")

        runner = LocalBoefjeJobRunner(local_repository)

        current_env = os.environ.copy()

        output = runner.run(meta, arguments)

        output_dict = ast.literal_eval(output[0][1].decode())

        # Assert that there are no overlapping environment keys
        assert not set(current_env.keys()) & set(output_dict.keys())

        # Assert that the original environment has been restored correctly
        assert current_env == os.environ

    def test_cannot_run_local_oci_boefje(self) -> None:
        meta = BoefjeMeta(
            id="b49cd6f5-4d92-4a13-9d21-232993826cd9",
            boefje={"id": "dummy_oci_boefje_no_main"},
            input_ooi="Network|internet",
            organization="_dev",
        )

        local_repository = LocalPluginRepository(Path(__file__).parent / "modules")
        runner = LocalBoefjeJobRunner(local_repository)

        with self.assertRaises(JobRuntimeError):
            runner.run(meta, {})

    def test_correct_local_runner_hash(self) -> None:
        """This test checks if calculating the hash of local boefjes returns the correct result"""

        local_repository = LocalPluginRepository(Path(__file__).parent / "modules")
        boefje_resource_1 = local_repository.by_id("dummy_boefje_environment")
        boefje_resource_2 = local_repository.by_id("dummy")

        # This boefje has a __pycache__ folder with *.pyc files, which should be ignored
        boefje_resource_3 = local_repository.by_id("dummy_boefje_environment_with_pycache")

        # Sanity check to make sure the .pyc files are actually there
        path = Path(__file__).parent / "modules" / "dummy_boefje_environment_with_pycache"
        assert Path(path / "some_subdir/cache.pyc").is_file()
        assert Path(path / "some_subdir/__init__.py").is_file()
        assert Path(path / "__pycache__/pytest__init__.cpython-311.pyc").is_file()
        assert Path(path / "__pycache__/pytest_main.cpython-311.pyc").is_file()

        assert boefje_resource_1.runnable_hash == "7450ebc13f6856df925e90cd57f2769468a39723f18ba835749982b484564ec9"
        assert boefje_resource_2.runnable_hash == "874e154b572a0315cfe4329bd3b756bf9cad77f6a87bb9b9b9bb6296f1d4b520"
        assert boefje_resource_3.runnable_hash == "70c0b0ad3b2e70fd79e52dcf043096a50ed69db1359df0011499e66ab1510bbe"
