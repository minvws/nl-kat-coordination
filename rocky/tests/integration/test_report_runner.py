from octopoes.api.models import Declaration
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models.ooi.reports import ReportRecipe

from rocky.scheduler import ReportTask
from tests.integration.conftest import seed_system


def test_run_report_task(octopoes_api_connector: OctopoesAPIConnector, report_runner, valid_time):
    seed_system(octopoes_api_connector, valid_time)

    recipe = ReportRecipe(
        recipe_id="8aa4e52b-812c-4cc2-8196-35fb8efc63ca",
        report_name_format="{report_type} for {ooi} in %Y",
        sub_report_name_format="{report_type} for {ooi} in %Y",
        input_recipe={"input_oois": "Network|internet"},
        report_types=["dns-report"],
        cron_expression="* * * * *"
    )
    octopoes_api_connector.save_declaration(Declaration(ooi=recipe, valid_time=valid_time))

    task = ReportTask(
        organisation_id=octopoes_api_connector.client, report_recipe_id="8aa4e52b-812c-4cc2-8196-35fb8efc63ca"
    )

    report_runner.run(task)
