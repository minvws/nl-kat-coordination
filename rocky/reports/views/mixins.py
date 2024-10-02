from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from tools.ooi_helpers import create_ooi

from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import Reference, ScanProfileType
from octopoes.models.exception import ObjectNotFoundException, TypeNotFound
from octopoes.models.ooi.reports import Report
from reports.report_types.aggregate_organisation_report.report import aggregate_reports
from reports.report_types.concatenated_report.report import ConcatenatedReport
from reports.report_types.helpers import REPORTS, get_report_by_id
from reports.views.base import BaseReportView, ReportDataDict
from rocky.bytes_client import BytesClient


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


def save_report_raw(bytes_client: BytesClient, data: dict) -> str:
    report_data_raw_id = bytes_client.upload_raw(
        raw=ReportDataDict(data).model_dump_json().encode(),
        manual_mime_types={"openkat/report"},
    )

    return report_data_raw_id


def save_report_data(
    bytes_client, observed_at, octopoes_api_connector, organization, plugin_data, report_data, report_names
):
    now = datetime.now(timezone.utc)

    # if it's not a single report, we need a parent
    if len(report_data) > 1 or len(list(report_data.values())[0]) > 1:
        raw_id = save_report_raw(bytes_client, data={"plugins": plugin_data})
        name = now.strftime(report_names[0][1])

        if not name or name.isspace():
            name = ConcatenatedReport.name

        parent_report_ooi = Report(
            name=str(name),
            report_type=str(ConcatenatedReport.id),
            template=ConcatenatedReport.template_path,
            report_id=uuid4(),
            organization_code=organization.code,
            organization_name=organization.name,
            organization_tags=list(organization.tags.all()),
            data_raw_id=raw_id,
            date_generated=datetime.now(timezone.utc),
            input_oois=[],
            observed_at=observed_at,
            parent_report=None,
            has_parent=False,
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

                raw_id = save_report_raw(bytes_client, data={"report_data": data["data"]})

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
                    organization_tags=list(organization.tags.all()),
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
        raw_id = save_report_raw(bytes_client, data={"report_data": data["data"], "plugins": plugin_data})
        report_type = get_report_by_id(report_type_id)
        name = now.strftime(report_names[0][1])

        if not name or name.isspace():
            name = ConcatenatedReport.name

        parent_report_ooi = Report(
            name=str(name),
            report_type=report_type_id,
            template=report_type.template_path,
            report_id=uuid4(),
            organization_code=organization.code,
            organization_name=organization.name,
            organization_tags=list(organization.tags.all()),
            data_raw_id=raw_id,
            date_generated=datetime.now(timezone.utc),
            input_oois=[ooi],
            observed_at=observed_at,
            parent_report=None,
            has_parent=False,
        )

        create_ooi(octopoes_api_connector, bytes_client, parent_report_ooi, observed_at)
    return parent_report_ooi


class SaveGenerateReportMixin(BaseReportView):
    def save_report(self, report_names: list) -> Report:
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
            self.get_plugin_data_for_saving(),
            report_data,
            report_names,
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
        input_oois = self.get_oois()
        organization = self.organization
        aggregate_report, post_processed_data, report_data, report_errors = aggregate_reports(
            self.octopoes_api_connector,
            input_oois,
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

        observed_at = self.get_observed_at()

        post_processed_data["plugins"] = self.get_plugin_data_for_saving()
        post_processed_data["oois"] = []
        for input_ooi in input_oois:
            post_processed_data["oois"].append(
                {
                    "name": input_ooi.human_readable,
                    "type": input_ooi.object_type,
                    "scan_profile_level": input_ooi.scan_profile.level.value if input_ooi.scan_profile else 0,
                    "scan_profile_type": (
                        input_ooi.scan_profile.scan_profile_type if input_ooi.scan_profile else ScanProfileType.EMPTY
                    ),
                }
            )

        post_processed_data["report_types"] = []
        for report_type in self.get_report_types():
            post_processed_data["report_types"].append(
                {
                    "name": str(report_type.name),
                    "description": str(report_type.description),
                    "label_style": report_type.label_style,
                }
            )

        now = datetime.utcnow()
        bytes_client = self.bytes_client

        # Save report data into bytes
        report_data_raw_id = save_report_raw(bytes_client, data=post_processed_data)

        report_type = type(aggregate_report)
        name = now.strftime(report_names[0][1])
        if not name or name.isspace():
            name = report_type.name

        report_ooi = Report(
            name=str(name),
            report_type=str(report_type.id),
            template=report_type.template_path,
            report_id=uuid4(),
            organization_code=organization.code,
            organization_name=organization.name,
            organization_tags=list(organization.tags.all()),
            data_raw_id=report_data_raw_id,
            date_generated=datetime.now(timezone.utc),
            input_oois=self.get_ooi_pks(),
            observed_at=observed_at,
            parent_report=None,
            has_parent=False,
        )
        create_ooi(self.octopoes_api_connector, bytes_client, report_ooi, observed_at)

        # Save the child reports to bytes
        for ooi, types in report_data.items():
            for report_type, data in types.items():
                save_report_raw(bytes_client, data=data)

        return report_ooi
