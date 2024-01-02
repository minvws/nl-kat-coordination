from pathlib import Path
from unittest import TestCase

from boefjes.job_models import NormalizerMeta
from boefjes.katalogus.local_repository import LocalPluginRepository
from boefjes.local import LocalNormalizerJobRunner
from tests.loading import get_dummy_data


class ADRValidatorNormalizerTest(TestCase):
    def test_no_findings(self):
        local_repository = LocalPluginRepository(Path(__file__).parent.parent / "boefjes" / "plugins")
        runner = LocalNormalizerJobRunner(local_repository)
        meta = NormalizerMeta.model_validate_json(get_dummy_data("adr-validator-normalize.json"))

        raw = """[{"rule": "TEST-01", "passed": true, "message": ""}]"""
        output = runner.run(meta, bytes(raw, "UTF-8"))

        self.assertEqual(1, len(output.observations))

        observation = output.observations[0]
        self.assertEqual(2, len(observation.results))

        self.assertEqual("APIDesignRule", observation.results[0].object_type)
        self.assertEqual("TEST-01", observation.results[0].name)
        self.assertEqual("APIDesignRuleResult", observation.results[1].object_type)
        self.assertEqual("", observation.results[1].message)
        self.assertTrue(observation.results[1].passed)

    def test_with_findings(self):
        local_repository = LocalPluginRepository(Path(__file__).parent.parent / "boefjes" / "plugins")
        runner = LocalNormalizerJobRunner(local_repository)
        meta = NormalizerMeta.model_validate_json(get_dummy_data("adr-validator-normalize.json"))

        raw = """[
            {"rule": "TEST-01", "passed": true, "message": ""},
            {"rule": "TEST-02", "passed": false, "message": "An error"},
            {"rule": "TEST-02", "passed": true, "message": ""}
        ]"""
        output = runner.run(meta, bytes(raw, "UTF-8"))

        self.assertEqual(1, len(output.observations))

        observation = output.observations[0]
        self.assertEqual(8, len(observation.results))

        self.assertEqual("APIDesignRule", observation.results[2].object_type)
        self.assertEqual("TEST-02", observation.results[2].name)
        self.assertEqual("APIDesignRuleResult", observation.results[3].object_type)
        self.assertEqual("An error", observation.results[3].message)
        self.assertFalse(observation.results[3].passed)

        self.assertEqual("ADRFindingType", observation.results[4].object_type)
        self.assertEqual("TEST-02", observation.results[4].id)
        self.assertEqual("Finding", observation.results[5].object_type)
        self.assertEqual("An error", observation.results[5].description)
        self.assertEqual("ADRFindingType|TEST-02", str(observation.results[5].finding_type))
