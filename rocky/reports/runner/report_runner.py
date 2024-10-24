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
        subreport_names = []
        oois_count = len(recipe.input_recipe["input_oois"])

        for report_type_id, data in report_data.items():
            report_type = get_report_by_id(report_type_id)

            for ooi in data:
                ooi_human_readable = Reference.from_str(ooi).human_readable
                subreport_name = recipe.subreport_name_format.replace("{ooi}", ooi_human_readable).replace(
                    "{report type}", str(report_type.name)
                )
                subreport_names.append((subreport_name, subreport_name))

        parent_report_name = recipe.report_name_format.replace("{oois_count}", str(oois_count))

        if "{ooi}" in parent_report_name and oois_count == 1:
            ooi = recipe.input_recipe["input_oois"][0]
            ooi_human_readable = Reference.from_str(ooi).human_readable
            parent_report_name = parent_report_name.replace("{ooi}", ooi_human_readable)
        if "{report type}" in parent_report_name and len(report_types) == 1:
            report_type = get_report_by_id(recipe.report_types[0])
            parent_report_name = parent_report_name.replace("{report type}", str(report_type.name))

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
            subreport_names,
            parent_report_name,
        )

        self.bytes_client.organization = None
