from datetime import datetime, timezone

from django.conf import settings
from tools.models import Organization

from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import Reference, ScanLevel, ScanProfileType
from octopoes.models.ooi.reports import ReportRecipe
from octopoes.models.types import type_by_name
from reports.report_types.aggregate_organisation_report.report import AggregateOrganisationReport, aggregate_reports
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
        recipe: ReportRecipe = connector.get(recipe_ref, valid_time)  # type: ignore

        report_types = [get_report_by_id(report_type_id) for report_type_id in recipe.asset_report_types]
        oois = []

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

        ooi_pks = [ooi for ooi in oois]

        self.bytes_client.organization = report_task.organisation_id

        if recipe.report_type == AggregateOrganisationReport.id:
            report_type_ids = [report.id for report in report_types]
            aggregate_report, post_processed_data, report_data, report_errors = aggregate_reports(
                connector, oois, report_type_ids, valid_time, report_task.organisation_id
            )
            save_aggregate_report_data(
                self.bytes_client,
                valid_time,
                connector,
                Organization.objects.get(code=report_task.organisation_id),
                ooi_pks,
                report_data,
                post_processed_data,
                aggregate_report,
                recipe,
            )
        else:
            error_reports, report_data = collect_reports(valid_time, connector, ooi_pks, report_types)

            save_report_data(
                self.bytes_client,
                valid_time,
                connector,
                Organization.objects.get(code=report_task.organisation_id),
                ooi_pks,
                report_data,
                recipe,
            )

        self.bytes_client.organization = None
