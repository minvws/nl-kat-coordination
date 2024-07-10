from pathlib import Path
from unittest import TestCase

import pytest
from pydantic import ValidationError

from boefjes.job_models import NormalizerMeta
from boefjes.local import LocalNormalizerJobRunner
from boefjes.local_repository import LocalPluginRepository
from tests.loading import get_dummy_data


class AnswerParserNormalizerTest(TestCase):
    def test_config_yielded(self):
        local_repository = LocalPluginRepository(Path(__file__).parent.parent / "boefjes" / "plugins")
        runner = LocalNormalizerJobRunner(local_repository)
        meta = NormalizerMeta.model_validate_json(get_dummy_data("answer-normalize.json"))

        with pytest.raises(TypeError):
            raw = '[{"key": "test"}]'
            runner.run(meta, bytes(raw, "UTF-8"))

        with pytest.raises(ValidationError):
            raw = '{"schema": "/bit/port-classification-ip", "answer": [{"key": "test"}]}'
            runner.run(meta, bytes(raw, "UTF-8"))

        raw = '{"schema": "/bit/port-classification-ip", "answer": {"key": "test"}}'
        output = runner.run(meta, bytes(raw, "UTF-8"))

        self.assertEqual(1, len(output.observations))
        self.assertEqual(1, len(output.observations[0].results))
        self.assertEqual("Config", output.observations[0].results[0].object_type)
