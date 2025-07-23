import json

from files.models import File
from octopoes.api.models import Declaration
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models.ooi.reports import ReportRecipe
from reports.runner.models import ReportTask
from reports.runner.report_runner import LocalReportRunner
from tests.integration.conftest import seed_system


def test_run_report_task(
    xtdb_octopoes_api_connector: OctopoesAPIConnector, report_runner: LocalReportRunner, valid_time
):
    oois = seed_system(xtdb_octopoes_api_connector, valid_time)

    recipe = ReportRecipe(
        recipe_id="abc4e52b-812c-4cc2-8196-35fb8efc63ca",
        report_type="concatenated-report",
        report_name_format="Concatenated report for ${oois_count} objects",
        input_recipe={"input_oois": [oois["hostnames"][0].reference, oois["hostnames"][1].reference]},
        asset_report_types=["dns-report"],
        cron_expression="* * * * *",
    )
    xtdb_octopoes_api_connector.save_declaration(Declaration(ooi=recipe, valid_time=valid_time))

    task = ReportTask(
        organisation_id=xtdb_octopoes_api_connector.xtdb_session.client.client, report_recipe_id=str(recipe.recipe_id)
    )
    report_runner.run(task)

    raw, raw2, raw3 = (file for file in File.objects.all())
    data = json.load(raw.file)
    data2 = json.load(raw2.file)
    data["input_data"]["plugins"]["required"] = set(data["input_data"]["plugins"]["required"])  # ordering issues
    data2["input_data"]["plugins"]["required"] = set(data2["input_data"]["plugins"]["required"])  # ordering issues

    first_asset_calls = [
        {
            "report_data": {
                "input_ooi": "Hostname|test|example.com",
                "records": [],
                "security": {"spf": True, "dkim": True, "dmarc": True, "dnssec": True, "caa": True},
                "finding_types": [],
            },
            "input_data": {
                "input_oois": ["Hostname|test|example.com"],
                "report_types": ["dns-report"],
                "plugins": {"required": {"dns-records", "dns-sec"}, "optional": ["dns-zone"]},
            },
        },
        {
            "report_data": {
                "input_ooi": "Hostname|test|a.example.com",
                "records": [],
                "security": {"spf": True, "dkim": True, "dmarc": True, "dnssec": True, "caa": True},
                "finding_types": [],
            },
            "input_data": {
                "input_oois": ["Hostname|test|a.example.com"],
                "report_types": ["dns-report"],
                "plugins": {"required": {"dns-records", "dns-sec"}, "optional": ["dns-zone"]},
            },
        },
    ]
    assert data in first_asset_calls
    assert data2 in first_asset_calls

    data_report = {
        "input_data": {
            "input_oois": {
                "AssetReport|Hostname|test|example.com|dns-report",
                "AssetReport|Hostname|test|a.example.com|dns-report",
            },
            "report_types": ["dns-report"],
            "plugins": {"required": {"dns-records", "dns-sec"}, "optional": ["dns-zone"]},
        }
    }

    report_data = json.load(raw3.file)

    # ordering issues
    report_data["input_data"]["plugins"]["required"] = set(report_data["input_data"]["plugins"]["required"])
    report_data["input_data"]["input_oois"] = set(report_data["input_data"]["input_oois"])

    assert report_data == data_report

    reports = xtdb_octopoes_api_connector.list_reports(valid_time)
    assert reports.count == 1

    assert reports.items[0].name == "Concatenated report for 2 objects"
    asset_reports = reports.items[0].input_oois
    assert len(asset_reports) == 2

    assert "DNS Report for a.example.com" in {x.name for x in asset_reports}
