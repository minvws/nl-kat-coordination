import json

from boefjes.job_models import NormalizerDeclaration, NormalizerMeta
from tests.loading import get_dummy_data


def test_report_data(normalizer_runner):
    meta = NormalizerMeta.model_validate_json(get_dummy_data("report-data-normalize.json"))

    raw = get_dummy_data("report-data.json")
    output = normalizer_runner.run(meta, raw)
    ooi_dict = json.loads(raw)

    declaration = NormalizerDeclaration(
        ooi={
            "object_type": "ReportData",
            "scan_profile": None,
            "primary_key": "ReportData|test",
            **ooi_dict,
        }
    )

    assert output.observations == []
    assert output.declarations == [declaration]
