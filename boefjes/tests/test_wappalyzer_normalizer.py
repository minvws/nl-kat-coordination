from pathlib import Path
from unittest import TestCase

from boefjes.job_models import NormalizerMeta
from boefjes.katalogus.local_repository import LocalPluginRepository
from boefjes.local import LocalNormalizerJobRunner
from tests.loading import get_dummy_data


class WappalyzerNormalizerTest(TestCase):
    def test_page_analyzer_normalizer(self):
        meta = NormalizerMeta.model_validate_json(get_dummy_data("body-page-analysis-normalize.json"))
        local_repository = LocalPluginRepository(Path(__file__).parent.parent / "boefjes" / "plugins")

        runner = LocalNormalizerJobRunner(local_repository)
        output = runner.run(meta, get_dummy_data("download_page_analysis.raw"))

        results = output.observations[0].results
        self.assertEqual(6, len(results))
        self.assertCountEqual(
            ["Software|jQuery Migrate|1.0.0|", "Software|jQuery|3.6.0|", "Software|Bootstrap|3.3.7|"],
            [o.primary_key for o in results if o.object_type == "Software"],
        )
