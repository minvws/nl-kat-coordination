from pathlib import Path

import sys
from datetime import datetime, timedelta
from os import environ
from unittest import TestCase
from unittest.mock import patch

from boefjes.plugins.models import Boefje, Normalizer
from boefjes.job import BoefjeMeta, NormalizerMeta
from boefjes.runner import (
    ModuleRunner,
    NormalizerJobRunner,
    NORMALIZER_SIGNATURE,
    OLD_BOEFJE_SIGNATURE,
    ModuleException,
    LocalBoefjeJobRunner,
)

Dummy = Boefje(
    id="dummy",
    name="dummy",
    module="modules.dummy_boefje",
    description="",
    input_ooi={},
    produces=set(),
    consumes=set(),
    dispatches={},
)

DummyWithException = Boefje(
    id="dummy",
    name="dummy",
    module="modules.dummy_boefje_runtime_exception",
    description="",
    input_ooi={},
    produces=set(),
    consumes=set(),
    dispatches={},
)


class TestRunner(TestCase):
    def setUp(self) -> None:
        self.boefje_meta = BoefjeMeta(
            id="test-job",
            boefje={"id": "dummy", "version": "9"},
            input_ooi="Hostname|internet|example.com",
            arguments={},
            organization="_dev",
        )
        self.boefje = Dummy
        self.normalizer = Normalizer(
            name="dummy_normalizer", module="modules.dummy_normalizer"
        )

        self.normalize_meta = NormalizerMeta(
            id="test-job",
            boefje_meta=self.boefje_meta,
            normalizer={"name": "dummy_normalizer", "version": "9"},
        )
        sys.path.append(str(Path(__file__).parent))

    def test_module_runner_resolve_module_invalid(self):
        self.assertRaises(
            ModuleNotFoundError,
            ModuleRunner("tests.modules.dummy", NORMALIZER_SIGNATURE, {}).run,
            self.normalize_meta,
            "not existing",
        )

    def test_module_runner_validate_module(self):
        ModuleRunner("tests.modules.dummy_boefje", OLD_BOEFJE_SIGNATURE, {}).run(
            self.boefje_meta
        )

    def test_module_runner_validate_module_invalid(self):
        module_runner = ModuleRunner(
            "tests.modules.dummy_boefje_missing_run", OLD_BOEFJE_SIGNATURE, {}
        )
        self.assertRaises(ModuleException, module_runner.run, self.boefje_meta)

    def test_boefje_module_runner_validate_module(self):
        module_runner = ModuleRunner(
            "tests.modules.dummy_boefje", OLD_BOEFJE_SIGNATURE, {}
        )

        module_runner.run(self.boefje_meta)

    def test_boefje_module_runner_validate_module_invalid(self):
        module_runner = ModuleRunner(
            "tests.modules.dummy_boefje_invalid_signature", OLD_BOEFJE_SIGNATURE, {}
        )

        self.assertRaises(ModuleException, module_runner.run, self.boefje_meta)

    def test_module_runner_with_extra_environment_keys(self):
        module_runner = ModuleRunner(
            "tests.modules.dummy_boefje_environment",
            OLD_BOEFJE_SIGNATURE,
            {"hello": "world"},
        )
        _, output = module_runner.run(self.boefje_meta)

        self.assertIn("hello", output.decode())
        self.assertNotIn("hello", environ)

    @patch("boefjes.runner.get_environment_settings", return_value={})
    @patch("boefjes.runner.datetime")
    def test_boefje_job_runner(self, mock_datetime, mock_get_environment_settings):
        mock_datetime.now.side_effect = [datetime(2020, 1, 1), datetime(2020, 1, 2)]
        job = self.boefje_meta.copy()

        runner = LocalBoefjeJobRunner(job, self.boefje, {})
        _, raw = runner.run()
        self.assertEqual(b"dummy-data", raw.data)
        self.assertNotEqual(self.boefje_meta, runner.boefje_meta)
        self.assertEqual(timedelta(1), runner.boefje_meta.runtime)

    def test_normalizer_job_runner(self):
        job = self.normalize_meta
        runner = NormalizerJobRunner(job, self.normalizer, b"test-network")
        runner.run()

        from octopoes.models.ooi.network import Network

        self.assertListEqual([Network(name="test-network")], runner.results)

    def test_normalizer_job_runner_skip_input_ooi(self):
        job = self.normalize_meta.copy()
        job.boefje_meta.input_ooi = (
            "Network|test-network"  # Input OOI the same as the OOI in the result set
        )

        runner = NormalizerJobRunner(job, self.normalizer, b"test-network")
        runner.run()

        self.assertListEqual([], runner.results)
