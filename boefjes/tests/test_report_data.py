import json
from pathlib import Path

from boefjes.job_models import NormalizerDeclaration, NormalizerMeta
from boefjes.katalogus.local_repository import LocalPluginRepository
from boefjes.local import LocalNormalizerJobRunner
from tests.loading import get_dummy_data


def test_report_data():
    local_repository = LocalPluginRepository(Path(__file__).parent.parent / "boefjes" / "plugins")
    runner = LocalNormalizerJobRunner(local_repository)
    meta = NormalizerMeta.model_validate_json(get_dummy_data("report-data-normalize.json"))

    raw = get_dummy_data("report-data.json")
    output = runner.run(meta, raw)
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
