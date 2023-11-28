from pathlib import Path
from unittest import TestCase

import pytest
from pydantic import ValidationError

from boefjes.job_models import NormalizerMeta
from boefjes.katalogus.local_repository import LocalPluginRepository
from boefjes.local import LocalNormalizerJobRunner
from tests.loading import get_dummy_data


class AnswerParserNormalizerTest(TestCase):
    def test_config_yielded(self):
        local_repository = LocalPluginRepository(Path(__file__).parent.parent / "boefjes" / "plugins")
        runner = LocalNormalizerJobRunner(local_repository)
        meta = NormalizerMeta.parse_raw(get_dummy_data("answer-normalize.json"))

        with pytest.raises(ValidationError):
            raw = '[{"key": 3}]'
            runner.run(meta, bytes(raw, "UTF-8"))

        raw = '{"key": 3}'
        output = runner.run(meta, bytes(raw, "UTF-8"))

        self.assertEqual(1, len(output.observations))
        self.assertEqual(1, len(output.observations[0].results))
        self.assertEqual("Config", output.observations[0].results[0].object_type)
