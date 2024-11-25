from datetime import datetime, timezone
from string import Template
from typing import Any
from uuid import uuid4

import structlog
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from tools.ooi_helpers import create_ooi

from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import Reference
from octopoes.models.exception import ObjectNotFoundException, TypeNotFound
from octopoes.models.ooi.reports import Report
from reports.report_types.aggregate_organisation_report.report import aggregate_reports
from reports.report_types.concatenated_report.report import ConcatenatedReport
from reports.report_types.definitions import BaseReport, SubReportPlugins
from reports.report_types.helpers import REPORTS, get_report_by_id
from reports.report_types.multi_organization_report.report import MultiOrganizationReport, collect_report_data
from reports.views.base import BaseReportView, ReportDataDict

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


def get_child_input_data(input_data: dict[str, Any], ooi: str, report_type: type[BaseReport]):
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
    bytes_client,
    observed_at,
    octopoes_api_connector,
    organization,
    input_data: dict,
    report_data,
    report_names,
    parent_report_name,
    report_recipe: Reference | None = None,
) -> Report | None:
    if len(report_data) == 0:
        return None

    now = datetime.now(timezone.utc)

    # if it's not a single report, we need a parent

    if len(report_data) > 1 or len(list(report_data.values())[0]) > 1:
        raw_id = bytes_client.upload_raw(
            raw=ReportDataDict(input_data).model_dump_json().encode(), manual_mime_types={"openkat/report"}
        )

        name = now.strftime(Template(parent_report_name).safe_substitute(report_type=str(ConcatenatedReport.name)))

        if not name or name.isspace():
            name = ConcatenatedReport.name

        parent_report_ooi = Report(
            name=str(name),
            report_type=str(ConcatenatedReport.id),
            template=ConcatenatedReport.template_path,
            report_id=uuid4(),
            organization_code=organization.code,
            organization_name=organization.name,
            organization_tags=[tag.name for tag in organization.tags.all()],
            data_raw_id=raw_id,
            date_generated=datetime.now(timezone.utc),
            input_oois=input_data["input_data"]["input_oois"],
            observed_at=observed_at,
            parent_report=None,
            has_parent=False,
            report_recipe=report_recipe,
        )

        create_ooi(octopoes_api_connector, bytes_client, parent_report_ooi, observed_at)

        for report_type_id, ooi_data in report_data.items():
            for ooi, data in ooi_data.items():
                name_to_save = ""
                report_type = get_report_by_id(report_type_id)
                report_type_name = str(report_type.name)

                ooi_name = Reference.from_str(ooi).human_readable
                for default_name, updated_name in report_names:
                    # Use default_name to check if we're on the right index in the list to update the name to save.
                    if ooi_name in default_name and report_type_name in default_name:
                        name_to_save = updated_name
                        break

                child_input_data = get_child_input_data(input_data, ooi, report_type)

                raw_id = bytes_client.upload_raw(
                    raw=ReportDataDict({"report_data": data["data"]} | child_input_data).model_dump_json().encode(),
                    manual_mime_types={"openkat/report"},
                )
                name = now.strftime(name_to_save)
                if not name or name.isspace():
                    name = ConcatenatedReport.name

                sub_report_ooi = Report(
                    name=str(name),
                    report_type=report_type_id,
                    template=report_type.template_path,
                    report_id=uuid4(),
                    organization_code=organization.code,
                    organization_name=organization.name,
                    organization_tags=[tag.name for tag in organization.tags.all()],
                    data_raw_id=raw_id,
                    date_generated=datetime.now(timezone.utc),
                    input_oois=[ooi],
                    observed_at=observed_at,
                    parent_report=parent_report_ooi.reference,
                    has_parent=True,
                )

                create_ooi(octopoes_api_connector, bytes_client, sub_report_ooi, observed_at)

    # if it's a single report we can just save it as complete
    else:
        report_type_id = next(iter(report_data))
        ooi = next(iter(report_data[report_type_id]))
        data = report_data[report_type_id][ooi]
        raw_id = bytes_client.upload_raw(
            raw=ReportDataDict({"report_data": data["data"]} | input_data).model_dump_json().encode(),
            manual_mime_types={"openkat/report"},
        )
        report_type = get_report_by_id(report_type_id)
        name = now.strftime(Template(parent_report_name).safe_substitute(report_type=str(report_type.name)))

        if not name or name.isspace():
            name = ConcatenatedReport.name

        parent_report_ooi = Report(
            name=str(name),
            report_type=report_type_id,
            template=report_type.template_path,
            report_id=uuid4(),
            organization_code=organization.code,
            organization_name=organization.name,
            organization_tags=[tag.name for tag in organization.tags.all()],
            data_raw_id=raw_id,
            date_generated=datetime.now(timezone.utc),
            input_oois=[ooi],
            observed_at=observed_at,
            parent_report=None,
            has_parent=False,
            report_recipe=report_recipe,
        )

        create_ooi(octopoes_api_connector, bytes_client, parent_report_ooi, observed_at)

    logger.info("Report created", event_code="080071", report=parent_report_ooi)
    return parent_report_ooi


def save_aggregate_report_data(
    bytes_client,
    octopoes_api_connector,
    organization,
    get_observed_at,
    ooi_pks,
    input_data: dict,
    parent_report_name,
    report_data,
    post_processed_data,
    aggregate_report,
    report_recipe: Reference | None = None,
) -> Report:
    observed_at = get_observed_at
    now = datetime.now(timezone.utc)

    # Create the report
    report_data_raw_id = bytes_client.upload_raw(
        raw=ReportDataDict(post_processed_data | input_data).model_dump_json().encode(),
        manual_mime_types={"openkat/report"},
    )
    report_type = type(aggregate_report)
    name = now.strftime(parent_report_name)
    if not name or name.isspace():
        name = report_type.name

    report_ooi = Report(
        name=str(name),
        report_type=str(report_type.id),
        template=report_type.template_path,
        report_id=uuid4(),
        organization_code=organization.code,
        organization_name=organization.name,
        organization_tags=[tag.name for tag in organization.tags.all()],
        data_raw_id=report_data_raw_id,
        date_generated=now,
        input_oois=ooi_pks,
        observed_at=observed_at,
        parent_report=None,
        has_parent=False,
        report_recipe=report_recipe,
    )
    create_ooi(octopoes_api_connector, bytes_client, report_ooi, observed_at)

    # Save the child reports to bytes

    for ooi, types in report_data.items():
        for report_type_id, data in types.items():
            report_type = get_report_by_id(report_type_id)
            child_input_data = get_child_input_data(input_data, ooi, report_type)

            raw_id = bytes_client.upload_raw(
                raw=ReportDataDict({"report_data": data} | child_input_data).model_dump_json().encode(),
                manual_mime_types={"openkat/report"},
            )

            aggregate_sub_report_ooi = Report(
                name=str(report_type.name),
                report_type=report_type_id,
                template=report_type.template_path,
                report_id=uuid4(),
                organization_code=organization.code,
                organization_name=organization.name,
                organization_tags=[tag.name for tag in organization.tags.all()],
                data_raw_id=raw_id,
                date_generated=now,
                input_oois=[ooi],
                observed_at=observed_at,
                parent_report=report_ooi.reference,
                has_parent=True,
            )

            create_ooi(octopoes_api_connector, bytes_client, aggregate_sub_report_ooi, observed_at)

    logger.info("Report created", event_code="080071", report=report_ooi)
    return report_ooi


class SaveGenerateReportMixin(BaseReportView):
    def save_report(self, report_names: list) -> Report | None:
        error_reports, report_data = collect_reports(
            self.observed_at,
            self.octopoes_api_connector,
            self.get_ooi_pks(),
            [x for x in self.get_report_types() if x in REPORTS],
        )

        parent_report_ooi = save_report_data(
            self.bytes_client,
            self.observed_at,
            self.octopoes_api_connector,
            self.organization,
            self.get_input_data(),
            report_data,
            report_names,
            report_names[0][1],
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

        return parent_report_ooi


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
            self.octopoes_api_connector,
            self.organization,
            self.get_observed_at(),
            self.get_ooi_pks(),
            self.get_input_data(),
            report_names[0][1],
            report_data,
            post_processed_data,
            aggregate_report,
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
            report_id=uuid4(),
            organization_code=self.organization.code,
            organization_name=self.organization.name,
            organization_tags=list(self.organization.tags.all()),
            data_raw_id=report_data_raw_id,
            date_generated=datetime.now(timezone.utc),
            input_oois=self.get_ooi_pks(),
            observed_at=observed_at,
            parent_report=None,
            has_parent=False,
        )

        create_ooi(self.octopoes_api_connector, self.bytes_client, report_ooi, observed_at)
        logger.info("Report created", event_code="080071", report=report_ooi)

        return report_ooi
