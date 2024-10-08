from datetime import datetime, timezone

from django.conf import settings
from katalogus.client import KATalogusError, get_katalogus
from tools.models import Organization

from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import Reference
from octopoes.models.ooi.reports import ReportRecipe
from reports.report_types.helpers import get_report_by_id
from reports.runner.models import JobRuntimeError, ReportJobRunner
from reports.views.base import format_plugin_data, hydrate_plugins
from reports.views.mixins import collect_reports, save_report_data
from rocky.bytes_client import get_bytes_client
from rocky.scheduler import ReportTask


class LocalReportJobRunner(ReportJobRunner):
    def run(self, report_task: ReportTask) -> None:
        now = datetime.now(timezone.utc)
        connector = OctopoesAPIConnector(settings.OCTOPOES_API, report_task.organisation_id)
        recipe: ReportRecipe = connector.get(
            Reference.from_str(f"ReportRecipe|{report_task.report_recipe_id}"), datetime.now(timezone.utc)
        )
        parsed_report_types = [get_report_by_id(report_type_id) for report_type_id in recipe.report_types]

        error_reports, report_data = collect_reports(
            now, connector, list(recipe.input_recipe["input_oois"]), parsed_report_types
        )

        try:
            report_type_plugins = hydrate_plugins(parsed_report_types, get_katalogus(report_task.organisation_id))
            plugins = format_plugin_data(report_type_plugins)
        except KATalogusError as e:
            raise JobRuntimeError("Failed to hydrate plugins from KATalogus") from e

        save_report_data(
            get_bytes_client(report_task.organisation_id),
            now,
            connector,
            Organization.objects.get(code=report_task.organisation_id),
            plugins,
            report_data,
            [(recipe.report_name_format, recipe.report_name_format)],
        )
