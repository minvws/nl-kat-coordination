import json

from reports.runner.report_runner import LocalReportRunner

from octopoes.api.models import Declaration
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models.ooi.reports import ReportRecipe
from rocky.health import ServiceHealth
from rocky.scheduler import ReportTask
from tests.integration.conftest import seed_system


def test_run_report_task(octopoes_api_connector: OctopoesAPIConnector, report_runner: LocalReportRunner, valid_time):
    oois = seed_system(octopoes_api_connector, valid_time)
    report_runner.bytes_client.health.return_value = ServiceHealth(service="bytes", healthy=True)
    report_runner.bytes_client.upload_raw.return_value = "abcdabcd-f8ab-4bdf-9b1b-58cd98ef6342"

    recipe = ReportRecipe(
        recipe_id="abc4e52b-812c-4cc2-8196-35fb8efc63ca",
        report_name_format="Concatenated report for ${oois_count} objects",
        asset_report_name_format="${report_type} for ${ooi} in %Y",
        input_recipe={"input_oois": [oois["hostnames"][0].reference, oois["hostnames"][1].reference]},
        asset_report_types=["dns-report"],
        cron_expression="* * * * *",
    )
    octopoes_api_connector.save_declaration(Declaration(ooi=recipe, valid_time=valid_time))

    task = ReportTask(organisation_id=octopoes_api_connector.client, report_recipe_id=str(recipe.recipe_id))
    report_runner.run(task)

    assert len(report_runner.bytes_client.upload_raw.mock_calls) == 3

    assert report_runner.bytes_client.upload_raw.mock_calls[0].kwargs["manual_mime_types"] == {"openkat/report"}
    assert report_runner.bytes_client.upload_raw.mock_calls[1].kwargs["manual_mime_types"] == {"openkat/report"}
    assert report_runner.bytes_client.upload_raw.mock_calls[2].kwargs["manual_mime_types"] == {"openkat/report"}

    data = json.loads(report_runner.bytes_client.upload_raw.mock_calls[0].kwargs["raw"])
    data["input_data"]["plugins"]["required"] = set(data["input_data"]["plugins"]["required"])  # ordering issues

    assert data == {
        "input_data": {
            "input_oois": ["Hostname|test|example.com", "Hostname|test|a.example.com"],
            "report_types": ["dns-report"],
            "plugins": {"required": {"dns-sec", "dns-records"}, "optional": ["dns-zone"]},
        }
    }

    # The order of the OOIs being processed is not guaranteed, so this is a simple workaround
    both_calls = [
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
                "plugins": {"required": {"dns-sec", "dns-records"}, "optional": ["dns-zone"]},
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
                "plugins": {"required": {"dns-sec", "dns-records"}, "optional": ["dns-zone"]},
            },
        },
    ]

    data_1 = json.loads(report_runner.bytes_client.upload_raw.mock_calls[1].kwargs["raw"])
    data_1["input_data"]["plugins"]["required"] = set(data_1["input_data"]["plugins"]["required"])  # ordering issues
    data_2 = json.loads(report_runner.bytes_client.upload_raw.mock_calls[2].kwargs["raw"])
    data_2["input_data"]["plugins"]["required"] = set(data_2["input_data"]["plugins"]["required"])  # ordering issues

    assert data_1 in both_calls
    assert data_2 in both_calls

    reports = octopoes_api_connector.list_reports(valid_time)
    assert reports.count == 1
    report, subreports = reports.items[0]
    assert len(subreports) == 2

    assert report.name == "Concatenated report for 2 objects"
    assert "DNS Report for a.example.com in 2024" in {x.name for x in subreports}

    # FIXME: the naming logic in reports/views/mixins.py 107-112 is not right. We expect to find example.com in this
    #  set, but instead only find a.example.com because when ooi_name is 'example.com', the check:
    #  `ooi_name in default_name` also passes for 'DNS Report for Hostname|test|a.example.com in %Y'.
    #  We shouldn't have to guess the match in the report_names argument. The name should be overridden on an object
    #  in the report_data list probably. Note that sometimes this does work when the OOIs are ordered differently.
