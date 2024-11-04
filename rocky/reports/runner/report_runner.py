from datetime import datetime, timezone
from string import Template

from django.conf import settings
from tools.models import Organization

from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import Reference
from reports.report_types.aggregate_organisation_report.report import AggregateOrganisationReport, aggregate_reports
from reports.report_types.definitions import report_plugins_union
from reports.report_types.helpers import get_report_by_id
from reports.runner.models import ReportRunner
from reports.views.mixins import collect_reports, save_aggregate_report_data, save_report_data
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
        oois_count = len(recipe.input_recipe["input_oois"])
        oois = []
        now = datetime.now(timezone.utc)

        for ooi_id in recipe.input_recipe["input_oois"]:
            ooi = connector.get(Reference.from_str(ooi_id), valid_time)
            oois.append(ooi)

        self.bytes_client.organization = report_task.organisation_id

        if recipe.parent_report_type == AggregateOrganisationReport.id:
            parent_report_name = now.strftime(
                Template(recipe.report_name_format).safe_substitute(
                    report_type=str(AggregateOrganisationReport.name), oois_count=str(oois_count)
                )
            )
            report_type_ids = [report.id for report in report_types]

            if "${ooi}" in parent_report_name and oois_count == 1:
                ooi = recipe.input_recipe["input_oois"][0]
                ooi_human_readable = Reference.from_str(ooi).human_readable
                parent_report_name = Template(parent_report_name).safe_substitute(ooi=ooi_human_readable)

            aggregate_report, post_processed_data, report_data, report_errors = aggregate_reports(
                connector, oois, report_type_ids, valid_time, report_task.organisation_id
            )
            save_aggregate_report_data(
                self.bytes_client,
                connector,
                Organization.objects.get(code=report_task.organisation_id),
                valid_time,
                recipe.input_recipe["input_oois"],
                {
                    "input_data": {
                        "input_oois": recipe.input_recipe["input_oois"],
                        "report_types": recipe.report_types,
                        "plugins": report_plugins_union(report_types),
                    }
                },
                parent_report_name,
                report_data,
                post_processed_data,
                aggregate_report,
            )
        else:
            subreport_names = []
            error_reports, report_data = collect_reports(
                valid_time, connector, recipe.input_recipe["input_oois"], report_types
            )

            for report_type_id, data in report_data.items():
                report_type = get_report_by_id(report_type_id)

                for ooi in data:
                    ooi_human_readable = Reference.from_str(ooi).human_readable
                    subreport_name = now.strftime(
                        Template(recipe.subreport_name_format).safe_substitute(
                            ooi=ooi_human_readable, report_type=str(report_type.name)
                        )
                    )
                    subreport_names.append((subreport_name, subreport_name))

            parent_report_name = now.strftime(
                Template(recipe.report_name_format).safe_substitute(oois_count=str(oois_count))
            )

            if "${ooi}" in parent_report_name and oois_count == 1:
                ooi = recipe.input_recipe["input_oois"][0]
                ooi_human_readable = Reference.from_str(ooi).human_readable
                parent_report_name = Template(parent_report_name).safe_substitute(ooi=ooi_human_readable)

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
