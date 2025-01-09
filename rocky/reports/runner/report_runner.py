from datetime import datetime, timezone
from string import Template

from django.conf import settings
from tools.models import Organization

from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import Reference, ScanLevel, ScanProfileType
from octopoes.models.ooi.reports import ReportRecipe
from octopoes.models.types import type_by_name
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
        # TODO: https://github.com/minvws/nl-kat-coordination/issues/4014
        valid_time = self.valid_time or datetime.now(timezone.utc)

        connector = OctopoesAPIConnector(
            settings.OCTOPOES_API, report_task.organisation_id, timeout=settings.ROCKY_OUTGOING_REQUEST_TIMEOUT
        )
        recipe_ref = Reference.from_str(f"ReportRecipe|{report_task.report_recipe_id}")
        recipe: ReportRecipe = connector.get(recipe_ref, valid_time)

        report_types = [get_report_by_id(report_type_id) for report_type_id in recipe.asset_report_types]
        oois = []
        now = datetime.now(timezone.utc)

        if input_oois := recipe.input_recipe.get("input_oois"):
            oois = connector.load_objects_bulk(set(input_oois), valid_time)
        elif query := recipe.input_recipe.get("query"):
            oois = connector.list_objects(
                types={type_by_name(ooi_type) for ooi_type in query["ooi_types"]},
                valid_time=datetime.now(tz=timezone.utc),
                scan_level={ScanLevel(level) for level in query["scan_level"]},
                scan_profile_type={ScanProfileType(scan_type) for scan_type in query["scan_type"]},
                search_string=query["search_string"],
                order_by=query["order_by"],
                asc_desc=query["asc_desc"],
            ).items

        ooi_count = len(oois)
        ooi_pks = [ooi.primary_key for ooi in oois]

        self.bytes_client.organization = report_task.organisation_id

        if recipe.report_type == AggregateOrganisationReport.id:
            report_name = now.strftime(
                Template(recipe.report_name_format).safe_substitute(
                    report_type=str(AggregateOrganisationReport.name), oois_count=str(ooi_count)
                )
            )
            report_type_ids = [report.id for report in report_types]

            if "${ooi}" in report_name and ooi_count == 1:
                report_name = Template(report_name).safe_substitute(ooi=oois[0].human_readable)

            aggregate_report, post_processed_data, report_data, report_errors = aggregate_reports(
                connector, oois, report_type_ids, valid_time, report_task.organisation_id
            )
            save_aggregate_report_data(
                self.bytes_client,
                valid_time,
                connector,
                Organization.objects.get(code=report_task.organisation_id),
                {
                    "input_data": {
                        "input_oois": ooi_pks,
                        "report_types": recipe.asset_report_types,
                        "plugins": report_plugins_union(report_types),
                    }
                },
                report_data,
                report_name,
                post_processed_data,
                aggregate_report,
                recipe_ref,
            )
        else:
            error_reports, report_data = collect_reports(valid_time, connector, ooi_pks, report_types)

            asset_report_names = []
            for report_type_id, data in report_data.items():
                report_type = get_report_by_id(report_type_id)

                for ooi in data:
                    ooi_human_readable = Reference.from_str(ooi).human_readable
                    asset_report_name = now.strftime(
                        Template(recipe.subreport_name_format).safe_substitute(
                            ooi=ooi_human_readable, report_type=str(report_type.name)
                        )
                    )
                    asset_report_names.append((asset_report_name, asset_report_name))

            report_name = now.strftime(Template(recipe.report_name_format).safe_substitute(oois_count=str(ooi_count)))

            if "${ooi}" in report_name and ooi_count == 1:
                report_name = Template(report_name).safe_substitute(ooi=ooi[0].human_readable)

            save_report_data(
                self.bytes_client,
                valid_time,
                connector,
                Organization.objects.get(code=report_task.organisation_id),
                {
                    "input_data": {
                        "input_oois": ooi_pks,
                        "report_types": recipe.asset_report_types,
                        "plugins": report_plugins_union(report_types),
                    }
                },
                report_data,
                asset_report_names,
                report_name,
                recipe_ref,
            )

            self.bytes_client.organization = None
