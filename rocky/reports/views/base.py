from collections import defaultdict
from collections.abc import Iterable, Sequence
from datetime import datetime, timezone
from logging import getLogger
from operator import attrgetter
from typing import Any
from uuid import uuid4

from account.mixins import OrganizationView
from django.contrib import messages
from django.forms import Form
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import urlencode
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from katalogus.client import Plugin, get_katalogus
from pydantic import RootModel, TypeAdapter
from tools.ooi_helpers import create_ooi
from tools.view_helpers import BreadcrumbsMixin

from octopoes.models import OOI, Reference
from octopoes.models.ooi.reports import Report as ReportOOI
from reports.forms import OOITypeMultiCheckboxForReportForm
from reports.report_types.definitions import AggregateReport, BaseReportType, MultiReport, Report, ReportType
from reports.report_types.helpers import get_plugins_for_report_ids, get_report_by_id
from rocky.views.mixins import OOIList
from rocky.views.ooi_view import OOIFilterView

REPORTS_PRE_SELECTION = {
    "clearance_level": ["2", "3", "4"],
    "clearance_type": "declared",
}


def get_selection(request: HttpRequest, pre_selection: dict[str, str | Sequence[str]] | None = None) -> str:
    if pre_selection is not None:
        return "?" + urlencode(pre_selection, True)
    return "?" + urlencode(request.GET, True)


logger = getLogger(__name__)


class ReportBreadcrumbs(OrganizationView, BreadcrumbsMixin):
    breadcrumbs_step: int = 1

    def get_kwargs(self):
        return {"organization_code": self.organization.code}

    def build_breadcrumbs(self):
        kwargs = self.get_kwargs()
        selection = get_selection(self.request)

        breadcrumbs = [
            {
                "url": reverse("reports", kwargs=kwargs) + selection,
                "text": _("Reports"),
            },
        ]

        return breadcrumbs

    def get_current(self):
        return self.build_breadcrumbs()[: self.breadcrumbs_step]

    def get_previous(self):
        breadcrumbs = self.build_breadcrumbs()
        if self.breadcrumbs_step >= 2:
            return self.build_breadcrumbs()[self.breadcrumbs_step - 2]["url"]
        return breadcrumbs[self.breadcrumbs_step]["url"]

    def get_next(self):
        breadcrumbs = self.build_breadcrumbs()
        if self.breadcrumbs_step < len(breadcrumbs):
            return breadcrumbs[self.breadcrumbs_step]["url"]
        return breadcrumbs[self.breadcrumbs_step - 1]["url"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = self.get_current()
        context["next"] = self.get_next()
        context["previous"] = self.get_previous()
        return context


class BaseReportView(OOIFilterView):
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.selected_oois = sorted(set(request.GET.getlist("ooi", [])))
        self.selected_report_types = request.GET.getlist("report_type", [])

        self.report_types: Sequence[type[Report] | type[MultiReport]] = self.get_report_types_from_choice()
        report_ids = [report.id for report in self.report_types]
        self.plugins, self.all_plugins_enabled = self.get_required_optional_plugins(
            get_plugins_for_report_ids(report_ids)
        )

    def get_oois(self) -> list[OOI]:
        if "all" in self.selected_oois:
            return self.octopoes_api_connector.list_objects(
                self.get_ooi_types(),
                valid_time=self.observed_at,
                limit=OOIList.HARD_LIMIT,
                scan_level=self.get_ooi_scan_levels(),
                scan_profile_type=self.get_ooi_profile_types(),
            ).items

        oois = []
        for ooi_id in self.selected_oois:
            try:
                oois.append(self.get_single_ooi(ooi_id))
            except Exception:
                logger.warning("No data could be found for '%s' ", ooi_id)
        return oois

    def get_ooi_filter_forms(self, ooi_types: Iterable[type[OOI]]) -> dict[str, Form]:
        return {
            "ooi_type_form": OOITypeMultiCheckboxForReportForm(
                sorted([ooi_class.get_ooi_type() for ooi_class in ooi_types]),
                self.request.GET,
            )
        }

    def get_report_types_for_generate_report(self, reports: set[type[BaseReportType]]) -> list[dict[str, str]]:
        return [
            {
                "id": report_type.id,
                "name": report_type.name,
                "description": report_type.description,
                "label_style": report_type.label_style,
            }
            for report_type in reports
        ]

    def get_report_types_for_aggregate_report(
        self, reports_dict: dict[str, set[type[Report]]]
    ) -> dict[str, list[dict[str, str]]]:
        report_types = {}
        for option, reports in reports_dict.items():
            report_types[option] = self.get_report_types_for_generate_report(reports)
        return report_types

    def get_required_optional_plugins(
        self, plugin_ids_dict: dict[str, set[str]]
    ) -> tuple[dict[str, list[Plugin]], dict[str, bool]]:
        all_plugins = get_katalogus(self.organization.code).get_plugins()
        sorted_plugins = sorted(all_plugins, key=attrgetter("name"))

        required_optional_plugins: dict[str, list[Plugin]] = {}
        plugins_enabled: dict[str, bool] = {}

        for required_optional, plugin_ids in plugin_ids_dict.items():
            plugins: list[Plugin] = []
            are_plugins_enabled: list[bool] = []
            for plugin in sorted_plugins:
                if plugin.id in plugin_ids:
                    plugins.append(plugin)
                    are_plugins_enabled.append(plugin.enabled)
            required_optional_plugins[required_optional] = plugins
            plugins_enabled[required_optional] = all(are_plugins_enabled)

        return required_optional_plugins, plugins_enabled

    def get_report_types_from_choice(self) -> list[type[Report] | type[MultiReport]]:
        report_types = []
        for report_type in self.selected_report_types:
            try:
                report = get_report_by_id(report_type)
                report_types.append(report)
            except ValueError:
                error_message = _("Report type '%s' does not exist.") % report_type
                messages.add_message(self.request, messages.ERROR, error_message)
        return report_types

    def get_report_types(self) -> list[ReportType]:
        return [
            {
                "id": report_type.id,
                "name": report_type.name,
                "description": report_type.description,
                "label_style": report_type.label_style,
            }
            for report_type in self.get_report_types_from_choice()
        ]

    def save_report(
        self,
        data: dict,
        report_type: ReportType | None,
        input_ooi: Reference | None,
        parent: Reference | None,
        has_parent: bool,
    ) -> ReportOOI:
        report_data_raw_id = self.bytes_client.upload_raw(
            raw=ReportDataDict(data).model_dump_json(), manual_mime_types={"openkat/report"}
        )

        report_ooi = ReportOOI(
            name="test_name",
            report_type=str(report_type.id) if report_type else None,
            template=report_type.template_path if report_type else None,
            report_id=uuid4(),
            organization_code=self.organization.code,
            organization_name=self.organization.name,
            organization_tags=list(self.organization.tags.all()),
            data_raw_id=report_data_raw_id,
            date_generated=datetime.now(timezone.utc),
            input_ooi=input_ooi,
            observed_at=self.observed_at,
            parent_report=parent,
            has_parent=has_parent,
        )

        create_ooi(
            api_connector=self.octopoes_api_connector,
            bytes_client=self.bytes_client,
            ooi=report_ooi,
            observed_at=self.observed_at,
        )

        return report_ooi

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["created_at"] = datetime.now()
        context["selected_oois"] = self.selected_oois
        context["selected_report_types"] = self.selected_report_types
        context["plugins"] = self.plugins
        context["oois"] = self.get_oois()
        return context


class ReportsLandingView(ReportBreadcrumbs, TemplateView):
    """
    Landing page for Reports.
    """

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return redirect(reverse("report_history", kwargs=self.get_kwargs()))


class ReportDataDict(RootModel):
    root: Any

    class Config:
        arbitrary_types_allowed = True


def recursive_dict():
    return defaultdict(recursive_dict)


class ViewReportView(BaseReportView, TemplateView):
    def get_template_names(self):
        if self.report_ooi.report_type and issubclass(get_report_by_id(self.report_ooi.report_type), AggregateReport):
            return [
                "aggregate_report.html",
            ]
        else:
            return [
                "generate_report.html",
            ]

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.report_id = request.GET.get("report_id", "")
        self.report_ooi = self.octopoes_api_connector.get(
            Reference.from_str(f"{self.report_id}"), valid_time=self.observed_at
        )

    def get_context_data(self, **kwargs):
        # TODO: add missing context fields
        # TODO: add template OOI
        context = super().get_context_data(**kwargs)

        if self.report_ooi.input_ooi:
            input_oois = [
                self.octopoes_api_connector.get(
                    Reference.from_str(self.report_ooi.input_ooi), valid_time=self.observed_at
                )
            ]
            human_readable = self.report_ooi.input_ooi.human_readable

        else:
            # TODO: get the input oois from the underlying reports
            input_oois = []
            human_readable = ""

        self.bytes_client.login()
        report_data: dict = {}
        if not self.report_ooi.report_type:
            # its multiple single reports
            children = self.octopoes_api_connector.query(
                "Report.<parent_report[is Report]", valid_time=self.observed_at, source=self.report_ooi.reference
            )
            for report in children:
                if report.report_type not in report_data:
                    report_data[report.report_type] = {}

                # Ensure the input_ooi exists within the report_type
                if report.input_ooi not in report_data[report.report_type]:
                    report_data[report.report_type][report.input_ooi] = {}

                # Set the data within the input_ooi
                report_data[report.report_type][report.input_ooi] = {
                    "data": TypeAdapter(Any, config={"arbitrary_types_allowed": True}).validate_json(
                        self.bytes_client.get_raw(raw_id=report.data_raw_id)
                    ),
                    "template": report.template,
                    "report_name": get_report_by_id(report.report_type).name,
                }
            context["report_data"] = report_data
        elif issubclass(get_report_by_id(self.report_ooi.report_type), AggregateReport):
            # its an aggregate report
            context["post_processed_data"] = TypeAdapter(Any, config={"arbitrary_types_allowed": True}).validate_json(
                self.bytes_client.get_raw(raw_id=self.report_ooi.data_raw_id)
            )
        else:
            # its a single report
            report_data[self.report_ooi.report_type] = {}
            report_data[self.report_ooi.report_type][self.report_ooi.input_ooi] = {
                "data": TypeAdapter(Any, config={"arbitrary_types_allowed": True}).validate_json(
                    self.bytes_client.get_raw(raw_id=self.report_ooi.data_raw_id)
                ),
                "template": self.report_ooi.template,
                "ooi_human_readable": human_readable,
                "report_name": get_report_by_id(self.report_ooi.report_type).name,
            }
            context["report_data"] = report_data

        context["created_at"] = self.report_ooi.date_generated
        context["selected_oois"] = input_oois
        context["oois"] = input_oois
        context["template"] = self.report_ooi.template
        return context
