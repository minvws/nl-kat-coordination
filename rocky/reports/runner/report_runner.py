from datetime import datetime, timezone

from django.conf import settings
from tools.models import Organization

from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import Reference
from reports.report_types.definitions import report_plugins_union
from reports.report_types.helpers import get_report_by_id
from reports.runner.models import ReportRunner
from reports.views.mixins import collect_reports, save_report_data
from rocky.bytes_client import BytesClient
from rocky.scheduler import ReportTask


class LocalReportRunner(ReportRunner):
    def __init__(self, bytes_client: BytesClient, valid_time: datetime | None = None):
        self.bytes_client = bytes_client
        self.valid_time = valid_time

    def run(self, report_task: ReportTask) -> None:
        valid_time = self.valid_time or datetime.now(timezone.utc)

        connector = OctopoesAPIConnector(settings.OCTOPOES_API, report_task.organisation_id)
        recipe = connector.get(Reference.from_str(f"ReportRecipe|{report_task.report_recipe_id}"), valid_time)
        report_types = [get_report_by_id(report_type_id) for report_type_id in recipe.report_types]

        error_reports, report_data = collect_reports(
            valid_time, connector, recipe.input_recipe["input_oois"], report_types
        )

        self.bytes_client.organization = report_task.organisation_id
        report_names = []
        oois_count = 0

        for report_type_id, data in report_data.items():
            oois_count += len(data)
            report_type = get_report_by_id(report_type_id)

            for ooi in data:
                report_name = recipe.subreport_name_format.replace("{ooi}", ooi).replace(
                    "{report type}", str(report_type.name)
                )
                report_names.append((report_name, report_name))

        save_report_data(
            self.bytes_client,
            valid_time,
            connector,
            Organization.objects.get(code=report_task.organisation_id),
            {
                "input_data": {
                    "input_oois": recipe.input_recipe["input_oois"],
                    "report_types": recipe.report_types,
                    "plugins": report_plugins_union(report_types),
                }
            },
            report_data,
            report_names,
            recipe.report_name_format.replace("{oois_count}", str(oois_count)),
        )

        self.bytes_client.organization = None
