from datetime import datetime, timezone
from string import Template
from typing import Any

import structlog
from django.conf import settings
from pydantic import RootModel
from tools.models import Organization
from tools.ooi_helpers import create_ooi

from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import Reference, ScanLevel, ScanProfileType
from octopoes.models.exception import ObjectNotFoundException, TypeNotFound
from octopoes.models.ooi.reports import AssetReport, Report, ReportRecipe
from octopoes.models.types import OOIType, type_by_name
from reports.report_types.aggregate_organisation_report.report import AggregateOrganisationReport
from reports.report_types.concatenated_report.report import ConcatenatedReport
from reports.report_types.definitions import BaseReport, SubReportPlugins, report_plugins_union
from reports.report_types.helpers import get_report_by_id
from reports.runner.models import ReportRunner
from rocky.bytes_client import BytesClient
from rocky.scheduler import ReportTask

logger = structlog.get_logger(__name__)


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

        if input_oois := recipe.input_recipe.get("input_oois"):
            oois = list(connector.load_objects_bulk(set(input_oois), valid_time).values())
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

        ooi_pks = [ooi.reference for ooi in oois]

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


def collect_reports(
    valid_time: datetime, octopoes_connector: OctopoesAPIConnector, input_oois: list[Reference], report_types
):
    error_reports = []
    report_data: dict[str, dict[str, dict[str, Any]]] = {}
    by_type: dict[str, list[str]] = {}

    for ooi in input_oois:
        ooi_type = ooi.class_

        if ooi_type not in by_type:
            by_type[ooi_type] = []

        by_type[ooi_type].append(ooi)

    for report_class in report_types:
        oois = {ooi for ooi_type in report_class.input_ooi_types for ooi in by_type.get(ooi_type.get_object_type(), [])}

        try:
            results = report_class(octopoes_connector).collect_data(oois, valid_time)
        except ObjectNotFoundException:
            error_reports.append(report_class.id)
            continue
        except TypeNotFound:
            error_reports.append(report_class.id)
            continue

        for ooi, data in results.items():
            if report_class.id not in report_data:
                report_data[report_class.id] = {}

            report_data[report_class.id][ooi] = {
                "data": data,
                "template": report_class.template_path,
                "report_name": report_class.name,
            }

    return error_reports, report_data


def save_report_data(
    bytes_client: BytesClient,
    observed_at: datetime,
    octopoes_api_connector: OctopoesAPIConnector,
    organization: Organization,
    oois: list[OOIType],
    report_data: dict,
    recipe: ReportRecipe,
) -> Report | None:
    now = datetime.now(timezone.utc)

    input_data = {
        "input_data": {
            "input_oois": oois,
            "report_types": recipe.asset_report_types,
            "plugins": report_plugins_union([get_report_by_id(type_id) for type_id in recipe.asset_report_types]),
        }
    }

    asset_reports = create_asset_reports(
        bytes_client, input_data, now, observed_at, octopoes_api_connector, organization, recipe, report_data
    )

    raw_id = bytes_client.upload_raw(
        raw=ReportDataDict(input_data).model_dump_json().encode(), manual_mime_types={"openkat/report"}
    )

    report_name = now.strftime(
        Template(recipe.report_name_format).safe_substitute(
            oois_count=str(len(oois)), report_type=str(ConcatenatedReport.name)
        )
    )

    if len(oois) == 1:
        report_name = Template(report_name).safe_substitute(ooi=oois[0].human_readable)

    if not report_name or report_name.isspace():
        report_name = ConcatenatedReport.name

    report_ooi = Report(
        name=str(report_name),
        report_type=str(ConcatenatedReport.id),
        template=ConcatenatedReport.template_path,
        organization_code=organization.code,
        organization_name=organization.name,
        organization_tags=[tag.name for tag in organization.tags.all()],
        data_raw_id=raw_id,
        date_generated=now,
        reference_date=observed_at,
        input_oois=[asset_report.reference for asset_report in asset_reports],
        observed_at=observed_at,
        report_recipe=recipe.reference,
    )

    create_ooi(octopoes_api_connector, bytes_client, report_ooi, observed_at)
    logger.info("Report created", event_code=800071, report=report_ooi)
    return report_ooi


def save_aggregate_report_data(
    bytes_client: BytesClient,
    observed_at: datetime,
    octopoes_api_connector: OctopoesAPIConnector,
    organization: Organization,
    oois: list[OOIType],
    report_data: dict,
    post_processed_data,
    recipe: ReportRecipe,
) -> Report | None:
    if len(report_data) == 0:
        return None

    now = datetime.now(timezone.utc)
    input_data = {
        "input_data": {
            "input_oois": oois,
            "report_types": recipe.asset_report_types,
            "plugins": report_plugins_union([get_report_by_id(type_id) for type_id in recipe.asset_report_types]),
        }
    }

    asset_reports = create_asset_reports(
        bytes_client, input_data, now, observed_at, octopoes_api_connector, organization, recipe, report_data
    )

    raw_id = bytes_client.upload_raw(
        raw=ReportDataDict(post_processed_data | input_data).model_dump_json().encode(),
        manual_mime_types={"openkat/report"},
    )
    report_name = now.strftime(
        Template(recipe.report_name_format).safe_substitute(
            report_type=str(AggregateOrganisationReport.name), oois_count=str(len(oois))
        )
    )

    if len(oois) == 1:
        report_name = Template(report_name).safe_substitute(ooi=oois[0].human_readable)

    if not report_name or report_name.isspace():
        report_name = AggregateOrganisationReport.name

    report_ooi = Report(
        name=str(report_name),
        report_type=str(AggregateOrganisationReport.id),
        template=AggregateOrganisationReport.template_path,
        organization_code=organization.code,
        organization_name=organization.name,
        organization_tags=[tag.name for tag in organization.tags.all()],
        data_raw_id=raw_id,
        date_generated=now,
        reference_date=observed_at,
        input_oois=[asset_report.reference for asset_report in asset_reports],
        observed_at=observed_at,
        report_recipe=recipe.reference,
    )
    create_ooi(octopoes_api_connector, bytes_client, report_ooi, observed_at)

    logger.info("Aggregate Report created", event_code=800071, report=report_ooi)
    return report_ooi


def create_asset_reports(
    bytes_client, input_data, now, observed_at, octopoes_api_connector, organization, recipe, report_data
):
    asset_reports = []

    for report_type_id, ooi_data in report_data.items():
        report_type = get_report_by_id(report_type_id)

        for ooi_reference, data in ooi_data.items():
            ooi_human_readable = ooi_reference.human_readable
            asset_report_name = now.strftime(
                Template(recipe.asset_report_name_format).safe_substitute(
                    ooi=ooi_human_readable, report_type=report_type.name
                )
            )

            asset_report_input = get_input_data(input_data, ooi_reference, report_type)
            asset_raw_id = bytes_client.upload_raw(
                raw=ReportDataDict({"report_data": data["data"]} | asset_report_input).model_dump_json().encode(),
                manual_mime_types={"openkat/report"},
            )

            asset_report = AssetReport(
                name=str(asset_report_name),
                report_type=report_type_id,
                report_recipe=recipe.reference,
                template=report_type.template_path,
                organization_code=organization.code,
                organization_name=organization.name,
                organization_tags=[tag.name for tag in organization.tags.all()],
                data_raw_id=asset_raw_id,
                date_generated=now,
                reference_date=observed_at,
                input_ooi=ooi_reference,
                observed_at=observed_at,
            )
            asset_reports.append(asset_report)
            create_ooi(octopoes_api_connector, bytes_client, asset_report, observed_at)

    return asset_reports


def get_input_data(input_data: dict[str, Any], ooi: str, report_type: type[BaseReport]):
    required_plugins = list(input_data["input_data"]["plugins"]["required"])
    optional_plugins = list(input_data["input_data"]["plugins"]["optional"])

    child_plugins: SubReportPlugins = {
        "required": [plugin_id for plugin_id in required_plugins if plugin_id in report_type.plugins["required"]],
        "optional": [plugin_id for plugin_id in optional_plugins if plugin_id in report_type.plugins["optional"]],
    }

    return {"input_data": {"input_oois": [ooi], "report_types": [report_type.id], "plugins": child_plugins}}


class ReportDataDict(RootModel):
    root: Any

    class Config:
        arbitrary_types_allowed = True


def aggregate_reports(
    connector: OctopoesAPIConnector,
    input_oois: list[Reference],
    selected_report_types: list[str],
    valid_time: datetime,
    organization_code: str,
) -> tuple[AggregateOrganisationReport, dict[str, Any], dict[str, Any], list[str]]:
    all_types = [
        t
        for t in AggregateOrganisationReport.reports["required"] + AggregateOrganisationReport.reports["optional"]
        if t.id in selected_report_types
    ]

    errors, report_data = collect_reports(valid_time, connector, input_oois, all_types)
    aggregate_report = AggregateOrganisationReport(connector)
    post_processed_data = aggregate_report.post_process_data(report_data, valid_time, organization_code)

    return aggregate_report, post_processed_data, report_data, errors
