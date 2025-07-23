from katalogus.boefjes.kat_wappalyzer.normalize import run
from katalogus.boefjes.normalizer_handler import LocalNormalizerHandler
from katalogus.worker.job_models import NormalizerMeta
from tests.conftest import get_dummy_data


def test_page_analyzer_normalizer():
    meta = NormalizerMeta.model_validate_json(get_dummy_data("body-page-analysis-normalize.json"))
    output = LocalNormalizerHandler._parse_results(
        meta, run(meta.raw_data.boefje_meta.input_ooi_data, get_dummy_data("download_page_analysis.raw"))
    )

    assert output.observations
    results = output.observations[0].results
    assert len(results) == 14
    assert {o.primary_key for o in results if o.object_type == "Software"} == {
        "Software|BootstrapCDN|3.3.7|",
        "Software|Bootstrap|3.3.7|cpe:2.3:a:getbootstrap:3.3.7:*:*:*:*:*:*:*:*",
        "Software|cdnjs||",
        "Software|jQuery Migrate|1.0.0|",
        "Software|jQuery|3.6.0|cpe:2.3:a:jquery:3.6.0:*:*:*:*:*:*:*:*",
        "Software|jQuery||cpe:2.3:a:jquery:jquery:*:*:*:*:*:*:*:*",
    }
