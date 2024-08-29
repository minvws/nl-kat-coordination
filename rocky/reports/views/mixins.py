from datetime import datetime
from typing import Any

from django.contrib import messages
from django.utils.translation import gettext_lazy as _

from octopoes.models import Reference, ScanProfileType
from octopoes.models.exception import ObjectNotFoundException, TypeNotFound
from octopoes.models.ooi.reports import Report as ReportOOI
from reports.report_types.aggregate_organisation_report.report import aggregate_reports
from reports.report_types.concatenated_report.report import ConcatenatedReport
from reports.report_types.helpers import REPORTS, get_report_by_id
from reports.views.base import ReportFinalSettingsView


class SaveGenerateReportMixin(ReportFinalSettingsView):
    def save_report(self, report_names: list) -> ReportOOI:
        error_reports = []
        report_data: dict[str, dict[str, dict[str, Any]]] = {}
        by_type: dict[str, list[str]] = {}

        number_of_reports = 0

        for ooi in self.report_recipe.input_oois:
            ooi_type = Reference.from_str(ooi).class_

            if ooi_type not in by_type:
                by_type[ooi_type] = []

            by_type[ooi_type].append(ooi)

        sorted_report_types = list(filter(lambda x: x in self.report_recipe.report_types, REPORTS))

        for report_class in sorted_report_types:
            oois = {
                ooi for ooi_type in report_class.input_ooi_types for ooi in by_type.get(ooi_type.get_object_type(), [])
            }

            try:
                results = report_class(self.octopoes_api_connector).collect_data(oois, self.observed_at)

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
                number_of_reports += 1

        observed_at = self.get_observed_at()
        now = datetime.utcnow()

        # if its not a single report, we need a parent
        if number_of_reports > 1:
            raw_id = self.save_report_raw(data={"plugins": self.get_plugin_data_for_saving()})
            report_ooi = self.save_report_ooi(
                report_data_raw_id=raw_id,
                report_type=ConcatenatedReport,
                input_oois=[],
                parent=None,
                has_parent=False,
                observed_at=observed_at,
                name=now.strftime(report_names[0][1]),
            )

            for report_type, ooi_data in report_data.items():
                for ooi, data in ooi_data.items():
                    name_to_save = ""

                    report_type_name = str(get_report_by_id(report_type).name)
                    ooi_name = Reference.from_str(ooi).human_readable
                    for default_name, updated_name in report_names:
                        # Use default_name to check if we're on the right index in the list to update the name to save.
                        if ooi_name in default_name and report_type_name in default_name:
                            name_to_save = updated_name
                            break

                    raw_id = self.save_report_raw(data={"report_data": data["data"]})

                    self.save_report_ooi(
                        report_data_raw_id=raw_id,
                        report_type=get_report_by_id(report_type),
                        input_oois=[ooi],
                        parent=report_ooi.reference,
                        has_parent=True,
                        observed_at=observed_at,
                        name=now.strftime(name_to_save),
                    )
        # if its a single report we can just save it as complete
        else:
            report_type = next(iter(report_data))
            ooi = next(iter(report_data[report_type]))
            data = report_data[report_type][ooi]
            raw_id = self.save_report_raw(
                data={"report_data": data["data"], "plugins": self.get_plugin_data_for_saving()}
            )
            report_ooi = self.save_report_ooi(
                report_data_raw_id=raw_id,
                report_type=get_report_by_id(report_type),
                input_oois=[ooi],
                parent=None,
                has_parent=False,
                observed_at=observed_at,
                name=now.strftime(report_names[0][1]),
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


class SaveAggregateReportMixin(ReportFinalSettingsView):
    def save_report(self, report_names: list) -> ReportOOI:
        input_oois = self.get_oois()

        aggregate_report, post_processed_data, report_data, report_errors = aggregate_reports(
            self.octopoes_api_connector,
            list(input_oois),
            self.report_recipe.report_types,
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

        # Create the report
        report_data_raw_id = self.save_report_raw(data=post_processed_data)
        report_ooi = self.save_report_ooi(
            report_data_raw_id=report_data_raw_id,
            report_type=type(aggregate_report),
            input_oois=[ooi.primary_key for ooi in input_oois],
            parent=None,
            has_parent=False,
            observed_at=observed_at,
            name=now.strftime(report_names[0][1]),
        )

        # Save the child reports to bytes
        for ooi, types in report_data.items():
            for report_type, data in types.items():
                self.save_report_raw(data=data)

        return report_ooi
