from datetime import datetime, timezone
from string import Template

from django.conf import settings
from tools.models import Organization

from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import Reference, ScanLevel, ScanProfileType
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
        valid_time = self.valid_time or datetime.now(timezone.utc)

        connector = OctopoesAPIConnector(
            settings.OCTOPOES_API, report_task.organisation_id, timeout=settings.ROCKY_OUTGOING_REQUEST_TIMEOUT
        )
        recipe_ref = Reference.from_str(f"ReportRecipe|{report_task.report_recipe_id}")
        recipe = connector.get(recipe_ref, valid_time)

        report_types = [get_report_by_id(report_type_id) for report_type_id in recipe.report_types]
        oois = []
        now = datetime.now(timezone.utc)

        if input_oois := recipe.input_recipe.get("input_oois"):
            for ooi_id in input_oois:
                ooi = connector.get(Reference.from_str(ooi_id), valid_time)
                oois.append(ooi)
        elif query := recipe.input_recipe.get("query"):
            types = {type_by_name(t) for t in query["ooi_types"]}
            scan_level = {ScanLevel(cl) for cl in query["scan_level"]}
            scan_type = {ScanProfileType(t) for t in query["scan_type"]}

            oois = connector.list_objects(
                types=types,
                valid_time=datetime.now(tz=timezone.utc),
                scan_level=scan_level,
                scan_profile_type=scan_type,
                search_string=query["search_string"],
                order_by=query["order_by"],
                asc_desc=query["asc_desc"],
            ).items

        oois_count = len(oois)
        ooi_pks = [ooi.primary_key for ooi in oois]

        self.bytes_client.organization = report_task.organisation_id

        if recipe.parent_report_type == AggregateOrganisationReport.id:
            parent_report_name = now.strftime(
                Template(recipe.report_name_format).safe_substitute(
                    report_type=str(AggregateOrganisationReport.name), oois_count=str(oois_count)
                )
            )
            report_type_ids = [report.id for report in report_types]

            if "${ooi}" in parent_report_name and oois_count == 1:
                parent_report_name = Template(parent_report_name).safe_substitute(ooi=oois[0].human_readable)

            aggregate_report, post_processed_data, report_data, report_errors = aggregate_reports(
                connector, oois, report_type_ids, valid_time, report_task.organisation_id
            )
            save_aggregate_report_data(
                self.bytes_client,
                connector,
                Organization.objects.get(code=report_task.organisation_id),
                valid_time,
                ooi_pks,
                {
                    "input_data": {
                        "input_oois": ooi_pks,
                        "report_types": recipe.report_types,
                        "plugins": report_plugins_union(report_types),
                    }
                },
                parent_report_name,
                report_data,
                post_processed_data,
                aggregate_report,
                recipe_ref,
            )
        else:
            subreport_names = []
            error_reports, report_data = collect_reports(valid_time, connector, ooi_pks, report_types)

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
                parent_report_name = Template(parent_report_name).safe_substitute(ooi=ooi[0].human_readable)

            save_report_data(
                self.bytes_client,
                valid_time,
                connector,
                Organization.objects.get(code=report_task.organisation_id),
                {
                    "input_data": {
                        "input_oois": ooi_pks,
                        "report_types": recipe.report_types,
                        "plugins": report_plugins_union(report_types),
                    }
                },
                report_data,
                subreport_names,
                parent_report_name,
                recipe_ref,
            )

            self.bytes_client.organization = None
