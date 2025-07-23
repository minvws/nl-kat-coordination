import json

from katalogus.boefjes.kat_report_data.normalize import run
from katalogus.boefjes.models import NormalizerDeclaration
from katalogus.boefjes.normalizer_handler import LocalNormalizerHandler
from katalogus.worker.job_models import NormalizerMeta
from tests.conftest import get_dummy_data


def test_report_data():
    meta = NormalizerMeta.model_validate_json(get_dummy_data("report-data-normalize.json"))

    raw = get_dummy_data("report-data.json")
    output = LocalNormalizerHandler._parse_results(meta, run(meta.raw_data.boefje_meta.input_ooi_data, raw))

    ooi_dict = json.loads(raw)

    declaration = NormalizerDeclaration(
        ooi={"object_type": "ReportData", "scan_profile": None, "primary_key": "ReportData|test", **ooi_dict}
    )

    assert output.observations == []
    assert output.declarations == [declaration]
