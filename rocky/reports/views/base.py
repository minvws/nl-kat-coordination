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
from katalogus.client import Boefje, KATalogusClientV1, KATalogusError, Plugin, get_katalogus
from pydantic import RootModel, TypeAdapter
from tools.ooi_helpers import create_ooi
from tools.view_helpers import BreadcrumbsMixin, PostRedirect, url_with_querystring

from octopoes.models import OOI, Reference
from octopoes.models.ooi.reports import Report as ReportOOI
from octopoes.models.ooi.reports import ReportRecipe
from reports.forms import OOITypeMultiCheckboxForReportForm
from reports.report_types.aggregate_organisation_report.report import AggregateOrganisationReport
from reports.report_types.concatenated_report.report import ConcatenatedReport
from reports.report_types.definitions import AggregateReport, BaseReport, Report, report_plugins_union
from reports.report_types.helpers import (
    REPORTS,
    get_ooi_types_from_aggregate_report,
    get_ooi_types_with_report,
    get_report_by_id,
    get_report_types_for_oois,
    get_report_types_from_aggregate_report,
)
from reports.report_types.multi_organization_report.report import MultiOrganizationReport
from reports.utils import JSONEncoder, debug_json_keys
from rocky.views.mixins import ObservedAtMixin, OOIList
from rocky.views.ooi_view import BaseOOIListView, OOIFilterView
from rocky.views.scheduler import SchedulerView

REPORTS_PRE_SELECTION = {"clearance_level": ["2", "3", "4"], "clearance_type": "declared"}


def get_selection(request: HttpRequest, pre_selection: dict[str, str | Sequence[str]] | None = None) -> str:
    if pre_selection is not None:
        return "?" + urlencode(pre_selection, True)
    return "?" + urlencode(request.GET, True)


logger = structlog.get_logger(__name__)


class ReportDataDict(RootModel):
    root: Any

    class Config:
        arbitrary_types_allowed = True


def recursive_dict():
    return defaultdict(recursive_dict)


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

        breadcrumbs = [{"url": reverse("reports", kwargs=kwargs) + selection, "text": _("Reports")}]

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


class ReportsLandingView(ReportBreadcrumbs, TemplateView):
    """
    Landing page for Reports.
    """

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return redirect(reverse("report_history", kwargs=self.get_kwargs()))


def hydrate_plugins(report_types: list[type["BaseReport"]], katalogus: KATalogusClientV1) -> dict[str, list[Plugin]]:
    plugins: dict[str, list[Plugin]] = {"required": [], "optional": []}
    merged_plugins = report_plugins_union(report_types)

    required_plugins_ids = list(merged_plugins["required"])
    optional_plugins_ids = list(merged_plugins["optional"])

    # avoid empty list getting all plugins from KATalogus
    if required_plugins_ids:
        plugins["required"] = sorted(katalogus.get_plugins(ids=required_plugins_ids), key=attrgetter("name"))
    if optional_plugins_ids:
        plugins["optional"] = sorted(katalogus.get_plugins(ids=optional_plugins_ids), key=attrgetter("name"))

    return plugins


def format_plugin_data(report_type_plugins: dict[str, list[Plugin]]):
    return [
        {
            "required": required_optional == "required",
            "enabled": plugin.enabled,
            "name": plugin.name,
            "scan_level": plugin.scan_level.value if isinstance(plugin, Boefje) else 0,
            "type": plugin.type,
            "description": plugin.description,
        }
        for required_optional, plugins in report_type_plugins.items()
        for plugin in plugins
    ]


class BaseReportView(OOIFilterView):
    """
    This view is the base for the report creation wizard.
    All the necessary functions and variables needed.
    """

    NONE_OOI_SELECTION_MESSAGE = _("Select at least one OOI to proceed.")
    NONE_REPORT_TYPE_SELECTION_MESSAGE = _("Select at least one report type to proceed.")

    report_type: type[BaseReport] | None = None  # Get report types from a specific report type ex. AggregateReport

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.selected_oois = self.get_ooi_pks()
        self.selected_report_types = self.get_report_type_ids()

    def get_ooi_selection(self) -> list[str]:
        return sorted(set(self.request.POST.getlist("ooi", [])))

    def all_oois_selected(self) -> bool:
        return "all" in self.request.GET.getlist("ooi", [])

    def get_ooi_pks(self) -> list[str]:
        if self.all_oois_selected():
            return sorted([ooi.primary_key for ooi in self.get_oois()])
        return self.get_ooi_selection()

    def get_total_oois(self):
        return len(self.selected_oois)

    def get_ooi_types(self):
        if self.report_type == AggregateOrganisationReport:
            return get_ooi_types_from_aggregate_report(AggregateOrganisationReport)
        if self.report_type == MultiOrganizationReport:
            return MultiOrganizationReport.input_ooi_types
        return get_ooi_types_with_report()

    def get_oois(self) -> list[OOI]:
        if self.all_oois_selected():
            return self.octopoes_api_connector.list_objects(
                self.get_ooi_types(),
                valid_time=self.observed_at,
                limit=OOIList.HARD_LIMIT,
                scan_level=self.get_ooi_scan_levels(),
                scan_profile_type=self.get_ooi_profile_types(),
            ).items

        return [self.get_single_ooi(pk=ooi_pk) for ooi_pk in self.get_ooi_selection()]

    def get_ooi_filter_forms(self) -> dict[str, Form]:
        return {
            "ooi_type_form": OOITypeMultiCheckboxForReportForm(
                sorted([ooi_class.get_ooi_type() for ooi_class in self.ooi_types]), self.request.GET
            )
        }

    def get_report_type_ids(self) -> list[str]:
        return sorted(set(self.request.POST.getlist("report_type", [])))

    def get_report_types(self) -> list[type[BaseReport]]:
        return [get_report_by_id(report_type_id) for report_type_id in self.selected_report_types]

    @staticmethod
    def get_report_types_from_ooi_selelection(
        report_types: set[type[BaseReport]] | set[type[Report]] | set[type[MultiOrganizationReport]],
    ) -> list[dict[str, str]]:
        """
        The report types are fetched from which ooi is selected. Shows all report types for the oois.
        """

        return [
            {
                "id": report_type.id,
                "name": report_type.name,
                "description": report_type.description,
                "label_style": report_type.label_style,
            }
            for report_type in report_types
        ]

    def get_report_types_for_generate_report(self):
        return self.get_report_types_from_ooi_selelection(get_report_types_for_oois(self.selected_oois))

    def get_report_types_for_aggregate_report(self) -> dict[str, list[dict[str, str]]]:
        reports_dict = get_report_types_from_aggregate_report(AggregateOrganisationReport)
        report_types: dict[str, list[dict[str, str]]] = {}

        for option, reports in reports_dict.items():
            report_types[option] = self.get_report_types_from_ooi_selelection(reports)
        return report_types

    def get_available_report_types(self) -> tuple[list[dict[str, str]] | dict[str, list[dict[str, str]]], int]:
        report_types: list[dict[str, str]] | dict[str, list[dict[str, str]]] = {}

        if self.report_type == AggregateOrganisationReport:
            report_types = self.get_report_types_for_aggregate_report()
            return report_types, len(
                [report_type for report_type_list in report_types.values() for report_type in report_type_list]
            )

        elif self.report_type == MultiOrganizationReport:
            report_types = self.get_report_types_from_ooi_selelection({MultiOrganizationReport})
            return report_types, len(report_types)

        report_types = self.get_report_types_for_generate_report()
        return report_types, len(report_types)

    def get_observed_at(self):
        return self.observed_at if self.observed_at < datetime.now(timezone.utc) else datetime.now(timezone.utc)

    def show_report_names(self) -> bool:
        recurrence_choice = self.request.POST.get("choose_recurrence", "once")
        return recurrence_choice == "once"

    def is_scheduled_report(self) -> bool:
        recurrence_choice = self.request.POST.get("choose_recurrence", "")
        return recurrence_choice == "repeat"

    def create_report_recipe(self, report_name_format: str, subreport_name_format: str, schedule: str) -> ReportRecipe:
        report_recipe = ReportRecipe(
            recipe_id=uuid4(),
            report_name_format=report_name_format,
            subreport_name_format=subreport_name_format,
            input_recipe={"input_oois": self.get_ooi_pks()},
            report_types=self.get_report_type_ids(),
            cron_expression=schedule,
        )
        create_ooi(
            api_connector=self.octopoes_api_connector,
            bytes_client=self.bytes_client,
            ooi=report_recipe,
            observed_at=datetime.now(timezone.utc),
        )
        return report_recipe

    def get_input_data(self) -> dict[str, Any]:
        return {
            "input_data": {
                "input_oois": self.get_ooi_pks(),
                "report_types": self.get_report_type_ids(),
                "plugins": report_plugins_union(self.get_report_types()),
            }
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["all_oois_selected"] = self.all_oois_selected()
        context["selected_oois"] = self.selected_oois
        context["selected_report_types"] = self.selected_report_types

        return context


class OOISelectionView(BaseReportView, BaseOOIListView):
    """
    Shows a list of OOIs to select from and handles OOIs selection requests.
    """

    def post(self, request, *args, **kwargs):
        if not (self.get_ooi_selection() or self.all_oois_selected()):
            messages.error(request, self.NONE_OOI_SELECTION_MESSAGE)
        return self.get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_ooi_filter_forms())
        return context


class ReportTypeSelectionView(BaseReportView, ReportBreadcrumbs, TemplateView):
    """
    Shows report types and handles selections and requests.
    """

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.available_report_types, self.counted_report_types = self.get_available_report_types()

    def post(self, request, *args, **kwargs):
        if not (self.get_ooi_selection() or self.all_oois_selected()):
            return PostRedirect(self.get_previous())
        return self.get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["oois"] = self.get_oois()  # show listed oois in report type view.
        context["total_oois"] = self.get_total_oois()  # adds counter to the heading

        context["available_report_types"] = self.available_report_types  # shows tiles of report types

        context["count_available_report_types"] = self.counted_report_types  # counter next to heading
        # especially for the CSS selector to set toggle on.
        context["all_report_types_checked"] = len(self.get_report_type_ids()) == self.counted_report_types

        return context


class ReportPluginView(BaseReportView, ReportBreadcrumbs, TemplateView):
    """
    This view shows the required and optional plugins together with the summary per report type.
    """

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.plugins = None

        try:
            self.plugins = hydrate_plugins(self.get_report_types(), get_katalogus(self.organization.code))
        except KATalogusError as error:
            messages.error(self.request, error.message)

    def post(self, request, *args, **kwargs):
        if self.plugins is None:
            return PostRedirect(self.get_previous())

        all_plugins_enabled = self.all_plugins_enabled()

        if not self.get_report_type_ids():
            messages.error(request, self.NONE_REPORT_TYPE_SELECTION_MESSAGE)
            return PostRedirect(self.get_previous())

        if "return" in self.request.POST and all_plugins_enabled:
            return PostRedirect(self.get_previous())

        if all_plugins_enabled:
            return PostRedirect(self.get_next())
        return self.get(request, *args, **kwargs)

    def all_plugins_enabled(self) -> bool:
        return all(self.plugins_enabled().values())

    def plugins_enabled(self) -> dict[str, bool]:
        if self.plugins is not None:
            return {
                "required": all([plugin.enabled for plugin in self.plugins["required"]]),
                "optional": all([plugin.enabled for plugin in self.plugins["optional"]]),
            }

        return {"required": False, "optional": False}

    def get_plugins_data(self):
        report_types: dict[str, Any] = {}
        plugin_report_types: dict[str, list] = {}
        total_enabled_plugins = {"required": 0, "optional": 0}
        total_available_plugins = {"required": 0, "optional": 0}

        if self.plugins is not None:
            for report_type in self.get_report_types():
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
                                {"name": report_type.name, "label_style": report_type.label_style}
                            ]
                        else:
                            plugin_report_types[plugin].append(
                                {"name": report_type.name, "label_style": report_type.label_style}
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["enabled_plugins"] = self.plugins_enabled()
        context["plugin_data"] = self.get_plugins_data()
        context["plugins"] = self.plugins
        return context


class ReportFinalSettingsView(BaseReportView, ReportBreadcrumbs, SchedulerView, TemplateView):
    report_type: type[BaseReport] | None = None
    task_type = "report"
    is_a_scheduled_report = False
    show_listes_report_names = False

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if not self.get_report_type_ids():
            messages.error(request, self.NONE_REPORT_TYPE_SELECTION_MESSAGE)
            return PostRedirect(self.get_previous())

        self.is_a_scheduled_report = self.is_scheduled_report()
        self.show_listes_report_names = self.show_report_names()

        return super().get(request, *args, **kwargs)

    @staticmethod
    def create_report_names(oois: list[OOI], report_types: list[type[BaseReport]]) -> dict[str, str]:
        reports = {}
        oois_count = len(oois)
        report_types_count = len(report_types)
        ooi = oois[0].human_readable
        report_type = report_types[0].name

        # Create name for parent report
        if not (report_types_count == 1 and oois_count == 1):
            if report_types_count > 1 and oois_count > 1:
                name = _("Concatenated Report for {oois_count} objects").format(
                    report_type=report_type, oois_count=oois_count
                )
            elif report_types_count > 1 and oois_count == 1:
                name = _("Concatenated Report for {ooi}").format(ooi=ooi)
            elif report_types_count == 1 and oois_count > 1:
                name = _("{report_type} for {oois_count} objects").format(
                    report_type=report_type, oois_count=oois_count
                )
            reports[name] = ""

        # Create name for subreports or single reports
        for ooi in oois:
            for report_type_ in report_types:
                name = _("{report_type} for {ooi}").format(report_type=report_type_.name, ooi=ooi.human_readable)
                reports[name] = ""

        return reports

    def get_report_names(self) -> dict[str, str] | list[str]:
        if self.report_type is not None and self.report_type == AggregateOrganisationReport:
            return [_("Aggregate Report")]
        if self.report_type is not None and self.report_type == MultiOrganizationReport:
            return [_("Multi Report")]

        return self.create_report_names(self.get_oois(), self.get_report_types())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["reports"] = self.get_report_names()

        context["report_schedule_form_recurrence_choice"] = self.get_report_schedule_form_recurrence_choice()
        context["report_schedule_form_recurrence"] = self.get_report_schedule_form_recurrence()

        context["report_parent_name_form"] = self.get_report_parent_name_form()
        context["report_child_name_form"] = self.get_report_child_name_form()

        context["show_listed_report_names"] = self.show_listes_report_names
        context["is_scheduled_report"] = self.is_a_scheduled_report

        context["created_at"] = datetime.now()
        return context


class SaveReportView(BaseReportView, ReportBreadcrumbs, SchedulerView):
    task_type = "report"

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        old_report_names = request.POST.getlist("old_report_name")
        report_names = request.POST.getlist("report_name", [])
        reference_dates = request.POST.getlist("reference_date")

        if self.show_report_names() and report_names:
            final_report_names = list(zip(old_report_names, self.finalise_report_names(report_names, reference_dates)))
            report_ooi = self.save_report(final_report_names)

            return redirect(
                reverse("view_report", kwargs={"organization_code": self.organization.code})
                + "?"
                + urlencode({"report_id": report_ooi.reference})
            )
        elif self.is_scheduled_report():
            report_name_format = request.POST.get("parent_report_name", "")
            subreport_name_format = request.POST.get("child_report_name", "")

            recurrence = request.POST.get("recurrence", "")

            schedule = self.convert_recurrence_to_cron_expressions(recurrence)

            report_recipe = self.create_report_recipe(report_name_format, subreport_name_format, schedule)

            self.create_report_schedule(report_recipe)

            return redirect(reverse("scheduled_reports", kwargs={"organization_code": self.organization.code}))

        messages.error(request, _("Empty name should not be possible."))
        return PostRedirect(self.get_previous())

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


class ViewReportView(ObservedAtMixin, OrganizationView, TemplateView):
    """
    This will display reports using report_id from reports history.
    Will fetch Report OOI and recreate report with data saved in bytes.
    """

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.report_ooi = self.get_report_ooi(request.GET.get("report_id"))
        self.report_data, self.input_oois, self.report_types, self.plugins = self.get_report_data()

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

    @property
    def custom_observed_at(self):
        return (
            self.observed_at.replace(hour=23, minute=59, second=59, microsecond=999999)
            if self.observed_at < datetime.now(timezone.utc)
            else datetime.now(timezone.utc).replace(hour=23, minute=59, second=59, microsecond=999999)
        )

    def get_report_ooi(self, ooi_pk: str) -> ReportOOI:
        return self.octopoes_api_connector.get(Reference.from_str(f"{ooi_pk}"), valid_time=self.custom_observed_at)

    def get_template_names(self):
        if self.report_ooi.report_type and issubclass(get_report_by_id(self.report_ooi.report_type), AggregateReport):
            return ["aggregate_report.html"]
        if self.report_ooi.report_type and issubclass(
            get_report_by_id(self.report_ooi.report_type), MultiOrganizationReport
        ):
            return ["multi_report.html"]
        return ["generate_report.html"]

    def get_children_reports(self) -> list[ReportOOI]:
        return [
            child
            for x in REPORTS
            for child in self.octopoes_api_connector.query(
                "Report.<parent_report[is Report]", valid_time=self.observed_at, source=self.report_ooi.reference
            )
            if child.report_type == x.id
        ]

    def get_input_oois(self, ooi_pks: list[str]) -> list[type[OOI]]:
        return [
            self.octopoes_api_connector.get(Reference.from_str(ooi), valid_time=self.observed_at) for ooi in ooi_pks
        ]

    def get_plugins(self, plugins_dict: dict[str, list[str]]) -> list[dict[str, list[Plugin]]]:
        plugins: dict[str, list[Plugin]] = {"required": [], "optional": []}

        plugin_ids_required = plugins_dict["required"]
        plugin_ids_optional = plugins_dict["optional"]

        katalogus_plugins = get_katalogus(self.organization.code).get_plugins(
            ids=plugin_ids_required + plugin_ids_optional
        )
        for plugin in katalogus_plugins:
            if plugin.id in plugin_ids_required:
                plugins["required"].append(plugin)
            if plugin.id in plugin_ids_optional:
                plugins["optional"].append(plugin)

        plugins["required"] = sorted(plugins["required"], key=attrgetter("enabled"))
        plugins["optional"] = sorted(plugins["optional"], key=attrgetter("enabled"), reverse=True)

        return format_plugin_data(plugins)

    def get_report_types(self, report_type_ids: Iterable[str]) -> list[dict[str, str]]:
        report_types = []
        for report_type_id in report_type_ids:
            report_type = get_report_by_id(report_type_id)
            report_types.append(
                {
                    "name": report_type.name,
                    "label_style": report_type.label_style,
                    "description": report_type.description,
                }
            )
        return report_types

    def get_report_data_from_bytes(self, report: ReportOOI) -> dict[str, Any]:
        self.bytes_client.login()
        return TypeAdapter(Any, config={"arbitrary_types_allowed": True}).validate_json(
            self.bytes_client.get_raw(raw_id=report.data_raw_id)
        )

    def get_report_data_single_report(
        self,
    ) -> tuple[
        dict[str, dict[str, dict[str, Any]]], list[type[OOI]], list[dict[str, Any]], list[dict[str, list[Plugin]]]
    ]:
        report_data: dict[str, Any] = self.get_report_data_from_bytes(self.report_ooi)

        report_types = self.get_report_types(report_data["input_data"]["report_types"])
        plugins = self.get_plugins(report_data["input_data"]["plugins"])
        oois = self.get_input_oois(self.report_ooi.input_oois)

        report_data[self.report_ooi.report_type] = {}

        for ooi in self.report_ooi.input_oois:
            report_data[self.report_ooi.report_type][ooi] = {
                "data": report_data["report_data"],
                "template": self.report_ooi.template,
                "report_name": self.report_ooi.name,
            } | report_data["input_data"]

        return report_data, oois, report_types, plugins

    def get_report_data_aggregate_report(
        self,
    ) -> tuple[
        dict[str, dict[str, dict[str, Any]]], list[type[OOI]], list[dict[str, Any]], list[dict[str, list[Plugin]]]
    ]:
        report_data = self.get_report_data_from_bytes(self.report_ooi)

        oois = self.get_input_oois(self.report_ooi.input_oois)
        report_types = self.get_report_types(report_data["input_data"]["report_types"])
        plugins = self.get_plugins(report_data["input_data"]["plugins"])

        return report_data, oois, report_types, plugins

    def get_report_data_concatenated_report(
        self,
    ) -> tuple[
        dict[str, dict[str, dict[str, Any]]], list[type[OOI]], list[dict[str, Any]], list[dict[str, list[Plugin]]]
    ]:
        report_data: dict[str, dict[str, dict[str, Any]]] = {}

        children_reports = self.get_children_reports()

        for report in children_reports:
            bytes_data = self.get_report_data_from_bytes(report)
            for ooi in report.input_oois:
                report_data.setdefault(report.report_type, {})[ooi] = {
                    "data": bytes_data["report_data"],
                    "template": report.template,
                    "report_name": report.name,
                } | bytes_data["input_data"]
        oois = self.get_input_oois(self.report_ooi.input_oois)
        report_type_ids = {child_report.report_type for child_report in children_reports}
        report_types = self.get_report_types(report_type_ids)
        plugins = self.get_plugins(self.get_report_data_from_bytes(self.report_ooi)["input_data"]["plugins"])

        return report_data, oois, report_types, plugins

    def get_report_data(self):
        if issubclass(get_report_by_id(self.report_ooi.report_type), ConcatenatedReport):
            return self.get_report_data_concatenated_report()
        if issubclass(get_report_by_id(self.report_ooi.report_type), AggregateReport):
            return self.get_report_data_aggregate_report()
        if issubclass(get_report_by_id(self.report_ooi.report_type), MultiOrganizationReport):
            return self.get_report_data_aggregate_report()

        return self.get_report_data_single_report()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["report_data"] = self.report_data
        context["report_ooi"] = self.report_ooi

        context["oois"] = self.input_oois

        context["report_types"] = self.report_types
        context["plugins"] = self.plugins

        context["report_download_pdf_url"] = url_with_querystring(
            reverse("view_report_pdf", kwargs={"organization_code": self.organization.code}), True, **self.request.GET
        )
        context["report_download_json_url"] = url_with_querystring(
            reverse("view_report", kwargs={"organization_code": self.organization.code}),
            True,
            **dict(json="true", **self.request.GET),
        )

        return context


class ViewReportPDFView(ViewReportView, WeasyTemplateResponseMixin):
    pdf_filename = "report.pdf"
    pdf_attachment = False
    pdf_options = {"pdf_variant": "pdf/ua-1"}

    def get_template_names(self):
        if self.report_ooi.report_type and issubclass(get_report_by_id(self.report_ooi.report_type), AggregateReport):
            return ["aggregate_report_pdf.html"]
        if self.report_ooi.report_type and issubclass(
            get_report_by_id(self.report_ooi.report_type), MultiOrganizationReport
        ):
            return ["multi_report_pdf.html"]
        return ["generate_report_pdf.html"]
