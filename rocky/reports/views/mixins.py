from datetime import datetime, timezone
from string import Template
from typing import Any

import structlog
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from tools.models import Organization
from tools.ooi_helpers import create_ooi

from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import Reference
from octopoes.models.exception import ObjectNotFoundException, TypeNotFound
from octopoes.models.ooi.reports import AssetReport, Report, ReportRecipe
from octopoes.models.types import OOIType
from reports.report_types.aggregate_organisation_report.report import AggregateOrganisationReport, aggregate_reports
from reports.report_types.concatenated_report.report import ConcatenatedReport
from reports.report_types.definitions import BaseReport, SubReportPlugins, report_plugins_union
from reports.report_types.helpers import REPORTS, get_report_by_id
from reports.report_types.multi_organization_report.report import MultiOrganizationReport, collect_report_data
from reports.views.base import BaseReportView, ReportDataDict
from rocky.bytes_client import BytesClient

logger = structlog.get_logger(__name__)


def collect_reports(observed_at: datetime, octopoes_connector: OctopoesAPIConnector, ooi_pks: list[str], report_types):
    error_reports = []
    report_data: dict[str, dict[str, dict[str, Any]]] = {}
    by_type: dict[str, list[str]] = {}

    for ooi in ooi_pks:
        ooi_type = Reference.from_str(ooi).class_

        if ooi_type not in by_type:
            by_type[ooi_type] = []

        by_type[ooi_type].append(ooi)

    for report_class in report_types:
        oois = {ooi for ooi_type in report_class.input_ooi_types for ooi in by_type.get(ooi_type.get_object_type(), [])}

        try:
            results = report_class(octopoes_connector).collect_data(oois, observed_at)
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


def get_input_data(input_data: dict[str, Any], ooi: str, report_type: type[BaseReport]):
    required_plugins = list(input_data["input_data"]["plugins"]["required"])
    optional_plugins = list(input_data["input_data"]["plugins"]["optional"])

    child_plugins: SubReportPlugins = {"required": [], "optional": []}

    child_plugins["required"] = [
        plugin_id for plugin_id in required_plugins if plugin_id in report_type.plugins["required"]
    ]
    child_plugins["optional"] = [
        plugin_id for plugin_id in optional_plugins if plugin_id in report_type.plugins["optional"]
    ]

    return {"input_data": {"input_oois": [ooi], "report_types": [report_type.id], "plugins": child_plugins}}


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


def create_asset_reports(
    bytes_client, input_data, now, observed_at, octopoes_api_connector, organization, recipe, report_data
):
    asset_reports = []

    for report_type_id, ooi_data in report_data.items():
        report_type = get_report_by_id(report_type_id)

        for ooi, data in ooi_data.items():
            ooi_human_readable = Reference.from_str(ooi).human_readable
            asset_report_name = now.strftime(
                Template(recipe.asset_report_name_format).safe_substitute(
                    ooi=ooi_human_readable, report_type=report_type.name
                )
            )

            asset_report_input = get_input_data(input_data, ooi, report_type)
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
                input_ooi=ooi,
                observed_at=observed_at,
            )
            asset_reports.append(asset_report)
            create_ooi(octopoes_api_connector, bytes_client, asset_report, observed_at)

    return asset_reports


def save_aggregate_report_data(
    bytes_client: BytesClient,
    observed_at: datetime,
    octopoes_api_connector: OctopoesAPIConnector,
    organization: Organization,
    oois: list[OOIType],
    report_data: dict,
    post_processed_data,
    aggregate_report,
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
        report_name = type(aggregate_report).name

    report_ooi = Report(
        name=str(report_name),
        report_type=str(type(aggregate_report).id),
        template=type(aggregate_report).template_path,
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


class SaveGenerateReportMixin(BaseReportView):
    def save_report(self, report_names: list) -> Report | None:
        error_reports, report_data = collect_reports(
            self.observed_at,
            self.octopoes_api_connector,
            self.get_ooi_pks(),
            [x for x in self.get_report_types() if x in REPORTS],
        )

        report_ooi = save_report_data(
            self.bytes_client,
            self.observed_at,
            self.octopoes_api_connector,
            self.organization,
            self.get_oois(),
            report_data,
            "Onboarding",  # TODO: Fix recipe
        )

        # If OOI could not be found or the date is incorrect, it will be shown to the user as a message error
        if error_reports:
            report_types = ", ".join(set(error_reports))
            date = self.observed_at.date()
            error_message = _("No data could be found for %(report_types). Object(s) did not exist on %(date)s.") % {
                "report_types": report_types,
                "date": date,
            }
            messages.error(self.request, error_message)

        return report_ooi


class SaveAggregateReportMixin(BaseReportView):
    def save_report(self, report_names: list) -> Report:
        aggregate_report, post_processed_data, report_data, report_errors = aggregate_reports(
            self.octopoes_api_connector,
            self.get_oois(),
            self.get_report_type_ids(),
            self.observed_at,
            self.organization.code,
        )

        # If OOI could not be found or the date is incorrect, it will be shown to the user as a message error
        if report_errors:
            report_types = ", ".join(set(report_errors))
            date = self.observed_at.date()
            error_message = _("No data could be found for %(report_types). Object(s) did not exist on %(date)s.") % {
                "report_types": report_types,
                "date": date,
            }
            messages.add_message(self.request, messages.ERROR, error_message)

        return save_aggregate_report_data(
            self.bytes_client,
            self.get_observed_at(),
            self.octopoes_api_connector,
            self.organization,
            self.get_oois(),
            report_data,
            post_processed_data,
            aggregate_report,
            "",  # TODO: fix recipe
        )


class SaveMultiReportMixin(BaseReportView):
    def save_report(self, report_names: list) -> Report:
        now = datetime.now(timezone.utc)

        observed_at = self.get_observed_at()
        report_type = MultiOrganizationReport(self.octopoes_api_connector)

        name = now.strftime(report_names[0][1])
        if not name or name.isspace():
            name = report_type.name

        report_data = report_type.post_process_data(
            collect_report_data(self.octopoes_api_connector, self.get_ooi_pks(), self.observed_at)
        )
        report_data_raw_id = self.bytes_client.upload_raw(
            ReportDataDict(report_data | self.get_input_data()).model_dump_json().encode(),
            manual_mime_types={"openkat/report"},
        )

        report_ooi = Report(
            name=str(name),
            report_type=str(report_type.id),
            template=report_type.template_path,
            organization_code=self.organization.code,
            organization_name=self.organization.name,
            organization_tags=list(self.organization.tags.all()),
            data_raw_id=report_data_raw_id,
            date_generated=now,
            reference_date=observed_at,  # TODO: https://github.com/minvws/nl-kat-coordination/issues/4014
            input_oois=self.get_ooi_pks(),
            observed_at=observed_at,
        )

        create_ooi(self.octopoes_api_connector, self.bytes_client, report_ooi, observed_at)
        logger.info("Report created", event_code=800071, report=report_ooi)

        return report_ooi
