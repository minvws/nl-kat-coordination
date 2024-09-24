from boefjes.job_models import NormalizerMeta
from tests.loading import get_dummy_data


def test_page_analyzer_normalizer(normalizer_runner):
    meta = NormalizerMeta.model_validate_json(get_dummy_data("body-page-analysis-normalize.json"))
    output = normalizer_runner.run(meta, get_dummy_data("download_page_analysis.raw"))

    results = output.observations[0].results
    assert len(results) == 6
    assert {o.primary_key for o in results if o.object_type == "Software"} == {
        "Software|jQuery Migrate|1.0.0|",
        "Software|jQuery|3.6.0|",
        "Software|Bootstrap|3.3.7|",
    }
