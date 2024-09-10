from collections import defaultdict
from collections.abc import Iterable, Sequence
from datetime import datetime, timezone
from operator import attrgetter
from typing import Any, Literal, cast
from uuid import uuid4

import structlog
from account.mixins import OrganizationView
from django.conf import settings
from django.contrib import messages
from django.forms import Form
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import urlencode
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from django_weasyprint import WeasyTemplateResponseMixin
from katalogus.client import Boefje, KATalogusError, Plugin, get_katalogus
from pydantic import RootModel, TypeAdapter
from tools.ooi_helpers import create_ooi
from tools.view_helpers import BreadcrumbsMixin, url_with_querystring

from octopoes.models import OOI, Reference
from octopoes.models.ooi.reports import Report as ReportOOI
from reports.forms import OOITypeMultiCheckboxForReportForm
from reports.report_types.concatenated_report.report import ConcatenatedReport
from reports.report_types.definitions import AggregateReport, BaseReportType, MultiReport, Report
from reports.report_types.helpers import REPORTS, get_plugins_for_report_ids, get_report_by_id
from reports.utils import JSONEncoder, debug_json_keys
from rocky.views.mixins import ObservedAtMixin, OOIList
from rocky.views.ooi_view import OOIFilterView

REPORTS_PRE_SELECTION = {
    "clearance_level": ["2", "3", "4"],
    "clearance_type": "declared",
}


def get_selection(request: HttpRequest, pre_selection: dict[str, str | Sequence[str]] | None = None) -> str:
    if pre_selection is not None:
        return "?" + urlencode(pre_selection, True)
    return "?" + urlencode(request.GET, True)


logger = structlog.get_logger(__name__)


class ReportBreadcrumbs(OrganizationView, BreadcrumbsMixin):
    breadcrumbs_step: int = 1

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.breadcrumbs = self.build_breadcrumbs()

    def get_kwargs(self):
        return {"organization_code": self.organization.code}

    def is_valid_breadcrumbs(self):
        return self.breadcrumbs_step < len(self.breadcrumbs)

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

    def get_breadcrumbs(self):
        if self.is_valid_breadcrumbs():
            return self.breadcrumbs[: self.breadcrumbs_step]
        return self.breadcrumbs

    def get_current(self):
        return self.breadcrumbs[self.breadcrumbs_step - 1]["url"]

    def get_previous(self):
        if self.is_valid_breadcrumbs() and self.breadcrumbs_step >= 2:
            return self.breadcrumbs[self.breadcrumbs_step - 2]["url"]
        return self.get_current()

    def get_next(self):
        if self.is_valid_breadcrumbs():
            return self.breadcrumbs[self.breadcrumbs_step]["url"]
        return self.get_current()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = self.get_breadcrumbs()
        context["next"] = self.get_next()
        context["previous"] = self.get_previous()
        return context


class OOISelectionView(OOIFilterView):
    """
    Shows a list of OOIs to select from and handles OOIs selection requests.
    """

    NONE_OOI_SELECTION_MESSAGE = _("Select at least one OOI to proceed.")

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.selected_oois: list[str] = self.get_ooi_selection()
        self.oois: list[OOI] = self.get_oois()
        self.oois_pk: list[str] = self.get_oois_pk()

    def get_ooi_selection(self) -> list[str]:
        selected_oois = self.request.GET.getlist("ooi", [])
        if "all" in selected_oois:
            return selected_oois
        return sorted(set(self.request.POST.getlist("ooi", [])))

    def get_total_objects(self) -> int:
        if "all" in self.selected_oois:
            return len(self.oois_pk)
        return len(self.selected_oois)

    def get_oois_pk(self) -> list[str]:
        oois_pk = self.selected_oois
        if "all" in self.selected_oois:
            oois_pk = [ooi.primary_key for ooi in self.oois]
        return oois_pk

    def get_oois(self) -> list[OOI]:
        if "all" in self.selected_oois:
            return self.octopoes_api_connector.list_objects(
                self.get_ooi_types(),
                valid_time=self.observed_at,
                limit=OOIList.HARD_LIMIT,
                scan_level=self.get_ooi_scan_levels(),
                scan_profile_type=self.get_ooi_profile_types(),
            ).items

        return [self.get_single_ooi(pk=ooi_pk) for ooi_pk in self.selected_oois]

    def get_ooi_filter_forms(self, ooi_types: Iterable[type[OOI]]) -> dict[str, Form]:
        return {
            "ooi_type_form": OOITypeMultiCheckboxForReportForm(
                sorted([ooi_class.get_ooi_type() for ooi_class in ooi_types]),
                self.request.GET,
            )
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["selected_oois"] = self.selected_oois
        context["oois_pk"] = self.oois_pk
        context["oois"] = self.oois
        context.update(self.get_ooi_filter_forms(self.ooi_types))
        return context


class ReportTypeSelectionView(TemplateView):
    """
    Shows report types and handles selections and requests.
    """

    NONE_REPORT_TYPE_SELECTION_MESSAGE = _("Select at least one report type to proceed.")

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.selected_report_types = self.get_report_type_selection()
        self.report_types: list[type[Report] | type[MultiReport] | type[AggregateReport]] = (
            self.get_report_types_from_choice()
        )
        self.report_type_ids = [report_type for report_type in self.selected_report_types]

    def get_report_type_selection(self) -> list[str]:
        return sorted(set(self.request.POST.getlist("report_type", [])))

    def get_report_types_from_choice(
        self,
    ) -> list[type[Report] | type[MultiReport] | type[AggregateReport]]:
        report_types = []
        for report_type in self.selected_report_types:
            try:
                report = get_report_by_id(report_type)
                report_types.append(report)
            except ValueError:
                error_message = _("Report type '%s' does not exist.") % report_type
                messages.error(self.request, error_message)
        return report_types

    @staticmethod
    def get_report_types(reports: set[type[BaseReportType]]) -> list[dict[str, str]]:
        return [
            {
                "id": report_type.id,
                "name": report_type.name,
                "description": report_type.description,
                "label_style": report_type.label_style,
            }
            for report_type in reports
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["selected_report_types"] = self.selected_report_types
        return context


class ReportPluginView(OOISelectionView, ReportTypeSelectionView):
    """
    This view shows the required and optional plugins.
    Needs ReportTypeView to know which report type is selected to get their plugins.
    The plugin ids will be collected and fetched form KAT-alogus.
    The user is able to activate plugins they need for the scans.
    The oois selection is also remembered by ReportOOIView.
    """

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        try:
            self.plugins, self.all_plugins_enabled = self.get_all_plugins()
        except KATalogusError as error:
            messages.error(self.request, error.message)
            self.plugins = {}
            self.all_plugins_enabled = {}

    def report_has_required_plugins(self) -> bool:
        if self.plugins:
            required_plugins = self.plugins["required"]
            return required_plugins != [] or required_plugins is not None
        return False

    def plugins_enabled(self) -> bool:
        if self.all_plugins_enabled:
            return self.all_plugins_enabled["required"] and self.all_plugins_enabled["optional"]
        return False

    def get_plugin_data_for_saving(self) -> list[dict]:
        plugin_data = []

        for required_optional, plugins in self.plugins.items():
            for plugin in plugins:
                plugin_data.append(
                    {
                        "required": required_optional == "required",
                        "enabled": plugin.enabled,
                        "name": plugin.name,
                        "scan_level": plugin.scan_level.value if isinstance(plugin, Boefje) else 0,
                        "type": plugin.type,
                        "description": plugin.description,
                    }
                )

        return plugin_data

    def get_all_plugins(self) -> tuple[dict[str, list[Plugin]], dict[str, bool]]:
        return self.get_required_optional_plugins(get_plugins_for_report_ids(self.report_type_ids))

    def get_required_optional_plugins(
        self, plugin_ids_dict: dict[str, set[str]]
    ) -> tuple[dict[str, list[Plugin]], dict[str, bool]]:
        required_optional_plugins: dict[str, list[Plugin]] = {}
        plugins_enabled: dict[str, bool] = {}

        for required_optional, plugin_ids in plugin_ids_dict.items():
            plugins: list[Plugin] = (
                get_katalogus(self.organization.code).get_plugins(ids=list(plugin_ids)) if plugin_ids else []
            )

            sorted_plugins = sorted(plugins, key=attrgetter("name"))
            are_plugins_enabled: list[bool] = []
            for plugin in sorted_plugins:
                are_plugins_enabled.append(plugin.enabled)
            required_optional_plugins[required_optional] = plugins
            plugins_enabled[required_optional] = all(are_plugins_enabled)

        return required_optional_plugins, plugins_enabled

    def get_plugin_data(self):
        report_types: dict[str, Any] = {}
        plugin_report_types: dict[str, list] = {}
        total_enabled_plugins = {"required": 0, "optional": 0}
        total_available_plugins = {"required": 0, "optional": 0}

        if self.plugins:
            for report_type in self.report_types:
                for plugin_type in ["required", "optional"]:
                    # Mypy doesn't infer this automatically https://github.com/python/mypy/issues/9168
                    plugin_type = cast(Literal["required", "optional"], plugin_type)
                    number_of_enabled = sum(
                        (1 if plugin.enabled and plugin.id in report_type.plugins[plugin_type] else 0)
                        for plugin in self.plugins[plugin_type]
                    )
                    report_plugins = report_type.plugins[plugin_type]

                    for plugin in report_plugins:
                        if plugin not in plugin_report_types:
                            plugin_report_types[plugin] = [
                                {
                                    "name": report_type.name,
                                    "label_style": report_type.label_style,
                                }
                            ]
                        else:
                            plugin_report_types[plugin].append(
                                {
                                    "name": report_type.name,
                                    "label_style": report_type.label_style,
                                }
                            )

                    total_enabled_plugins[plugin_type] += number_of_enabled
                    total_available_plugins[plugin_type] += len(report_plugins)

                    if report_type.name not in report_types:
                        report_types[report_type.name] = {}

                    report_types[report_type.name][f"number_of_enabled_{plugin_type}"] = number_of_enabled
                    report_types[report_type.name][f"number_of_available_{plugin_type}"] = len(report_plugins)

        plugin_data = {
            "total_enabled_plugins": total_enabled_plugins,
            "total_available_plugins": total_available_plugins,
            "report_types": report_types,
            "plugin_report_types": plugin_report_types,
        }

        return plugin_data

    @staticmethod
    def finalise_report_names(report_names: list[str], reference_dates: list[str]) -> list[str]:
        final_report_names = []

        if len(report_names) == len(reference_dates):
            for index, report_name in enumerate(report_names):
                date_format = ""
                if reference_dates[index] and reference_dates[index] != "":
                    date_format = " - "
                    if reference_dates[index] == "week":
                        date_format += _("Week %W, %Y")
                    else:
                        date_format += reference_dates[index]
                final_report_name = f"{report_name} {date_format}".strip()
                final_report_names.append(final_report_name)
        if not final_report_names:
            return report_names
        return final_report_names

    def save_report_raw(self, data: dict) -> str:
        report_data_raw_id = self.bytes_client.upload_raw(
            raw=ReportDataDict(data).model_dump_json().encode(),
            manual_mime_types={"openkat/report"},
        )

        return report_data_raw_id

    def save_report_ooi(
        self,
        report_data_raw_id: str,
        report_type: type[Report] | type[MultiReport] | type[AggregateReport],
        input_oois: list[str],
        parent: Reference | None,
        has_parent: bool,
        observed_at: datetime,
        name: str,
    ) -> ReportOOI:
        if not name or name.isspace():
            name = report_type.name
        report_ooi = ReportOOI(
            name=str(name),
            report_type=str(report_type.id),
            template=report_type.template_path,
            report_id=uuid4(),
            organization_code=self.organization.code,
            organization_name=self.organization.name,
            organization_tags=list(self.organization.tags.all()),
            data_raw_id=report_data_raw_id,
            date_generated=datetime.now(timezone.utc),
            input_oois=input_oois,
            observed_at=observed_at,
            parent_report=parent,
            has_parent=has_parent,
        )

        create_ooi(
            api_connector=self.octopoes_api_connector,
            bytes_client=self.bytes_client,
            ooi=report_ooi,
            observed_at=observed_at,
        )

        return report_ooi

    def get_observed_at(self):
        return self.observed_at if self.observed_at < datetime.now(timezone.utc) else datetime.now(timezone.utc)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["created_at"] = datetime.now()
        context["plugins"] = self.plugins
        context["all_plugins_enabled"] = self.all_plugins_enabled
        context["plugin_data"] = self.get_plugin_data()
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


class ViewReportView(ObservedAtMixin, OrganizationView, TemplateView):
    """
    This will display reports using report_id from reports history.
    Will fetch Report OOI and recreate report with data saved in bytes.
    """

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.report_ooi = self.get_report_ooi(request.GET.get("report_id"))
        self.report_data, self.input_oois, self.report_types = self.get_report_data()

    def get(self, request, *args, **kwargs):
        if "json" in self.request.GET and self.request.GET["json"] == "true":
            response = {
                "organization_code": self.organization.code,
                "organization_name": self.organization.name,
                "organization_tags": list(self.organization.tags.all()),
                "data": self.report_data,
            }

            try:
                response = JsonResponse(response, encoder=JSONEncoder)
            except TypeError:
                # We can't use translated strings as keys in JSON. This
                # debugging code makes it easy to spot where the problem is.
                if settings.DEBUG:
                    debug_json_keys(self.report_data, [])
                raise
            else:
                response["Content-Disposition"] = f"attachment; filename=report-{self.organization.code}.json"
                return response

        return super().get(request, *args, **kwargs)

    def get_report_ooi(self, ooi_pk: str) -> ReportOOI:
        return self.octopoes_api_connector.get(Reference.from_str(f"{ooi_pk}"), valid_time=self.observed_at)

    def get_template_names(self):
        if self.report_ooi.report_type and issubclass(get_report_by_id(self.report_ooi.report_type), AggregateReport):
            return [
                "aggregate_report.html",
            ]
        else:
            return [
                "generate_report.html",
            ]

    def get_children_reports(self) -> list[ReportOOI]:
        return [
            child
            for x in REPORTS
            for child in self.octopoes_api_connector.query(
                "Report.<parent_report[is Report]",
                valid_time=self.observed_at,
                source=self.report_ooi.reference,
            )
            if child.report_type == x.id
        ]

    @staticmethod
    def get_report_types(reports: list[ReportOOI]) -> list[dict[str, Any]]:
        return [report.class_attributes() for report in {get_report_by_id(report.report_type) for report in reports}]

    def get_report_data_from_bytes(self, report: ReportOOI) -> dict[str, Any]:
        return TypeAdapter(Any, config={"arbitrary_types_allowed": True}).validate_json(
            self.bytes_client.get_raw(raw_id=report.data_raw_id)
        )

    def get_input_oois(self, reports: list[ReportOOI]) -> list[type[OOI]]:
        ooi_pks = {ooi for report in reports for ooi in report.input_oois}

        return [
            self.octopoes_api_connector.get(Reference.from_str(ooi), valid_time=self.observed_at) for ooi in ooi_pks
        ]

    def get_report_data_single_report(
        self,
    ) -> tuple[dict[str, dict[str, dict[str, Any]]], list[type[OOI]], list[dict[str, Any]]]:
        self.bytes_client.login()
        report_data: dict[str, dict[str, dict[str, Any]]] = {}
        report_data[self.report_ooi.report_type] = {}

        for ooi in self.report_ooi.input_oois:
            report_data[self.report_ooi.report_type][ooi] = {
                "data": self.get_report_data_from_bytes(self.report_ooi)["report_data"],
                "template": self.report_ooi.template,
                "report_name": self.report_ooi.name,
            }

        input_oois = self.get_input_oois([self.report_ooi])
        report_types = self.get_report_types([self.report_ooi])

        return report_data, input_oois, report_types

    def get_report_data_aggregate_report(
        self,
    ) -> tuple[dict[str, dict[str, dict[str, Any]]], list[type[OOI]], list[dict[str, Any]]]:
        self.bytes_client.login()
        report_data = self.get_report_data_from_bytes(self.report_ooi)

        children_reports = self.get_children_reports()
        input_oois = self.get_input_oois([self.report_ooi])
        report_types = self.get_report_types(children_reports)

        return report_data, input_oois, report_types

    def get_report_data_concatenated_report(
        self,
    ) -> tuple[dict[str, dict[str, dict[str, Any]]], list[type[OOI]], list[dict[str, Any]]]:
        self.bytes_client.login()
        report_data: dict[str, dict[str, dict[str, Any]]] = {}

        children_reports = self.get_children_reports()
        input_oois = self.get_input_oois(children_reports)
        report_types = self.get_report_types(children_reports)

        for report in children_reports:
            for ooi in report.input_oois:
                report_data.setdefault(report.report_type, {})[ooi] = {
                    "data": self.get_report_data_from_bytes(report)["report_data"],
                    "template": report.template,
                    "report_name": report.name,
                }
        return report_data, input_oois, report_types

    def get_report_data(self):
        if issubclass(get_report_by_id(self.report_ooi.report_type), ConcatenatedReport):
            return self.get_report_data_concatenated_report()
        elif issubclass(get_report_by_id(self.report_ooi.report_type), AggregateReport):
            return self.get_report_data_aggregate_report()
        else:
            return self.get_report_data_single_report()

    def get_context_data(self, **kwargs):
        # TODO: add config and plugins
        # TODO: add template OOI
        context = super().get_context_data(**kwargs)
        context["report_data"] = self.report_data

        context["report_name"] = self.report_ooi.name
        context["report_types"] = [
            report_type for x in REPORTS for report_type in self.report_types if report_type["id"] == x.id
        ]
        context["created_at"] = self.report_ooi.date_generated
        context["observed_at"] = self.report_ooi.observed_at
        context["total_oois"] = len(self.input_oois)
        context["oois"] = self.input_oois

        context["template"] = self.report_ooi.template
        context["report_download_pdf_url"] = url_with_querystring(
            reverse(
                "view_report_pdf",
                kwargs={"organization_code": self.organization.code},
            ),
            True,
            **self.request.GET,
        )
        context["report_download_json_url"] = url_with_querystring(
            reverse(
                "view_report",
                kwargs={"organization_code": self.organization.code},
            ),
            True,
            **dict(json="true", **self.request.GET),
        )

        return context


class ViewReportPDFView(ViewReportView, WeasyTemplateResponseMixin):
    pdf_filename = "report.pdf"
    pdf_attachment = False
    pdf_options = {
        "pdf_variant": "pdf/ua-1",
    }

    def get_template_names(self):
        if self.report_ooi.report_type and issubclass(get_report_by_id(self.report_ooi.report_type), AggregateReport):
            return [
                "aggregate_report_pdf.html",
            ]
        else:
            return [
                "generate_report_pdf.html",
            ]
