from collections.abc import Iterable, Sequence
from datetime import datetime
from logging import getLogger
from typing import Any

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
from tools.view_helpers import BreadcrumbsMixin

from octopoes.models import OOI
from reports.forms import OOITypeMultiCheckboxForReportForm
from reports.report_types.definitions import BaseReportType, MultiReport, Report, ReportType
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
    current_step: int = 1

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
        return self.build_breadcrumbs()[: self.current_step]

    def get_previous(self):
        return self.build_breadcrumbs()[self.current_step - 2]["url"]

    def get_next(self):
        breadcrumbs = self.build_breadcrumbs()
        if self.current_step < len(breadcrumbs):
            return breadcrumbs[self.current_step]["url"]
        return breadcrumbs[self.current_step - 1]["url"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = self.get_current()
        context["next"] = self.get_next()
        context["previous"] = self.get_previous()
        return context


class BaseReportView(OOIFilterView):
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.selected_oois = list(set(request.GET.getlist("ooi", [])))
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
                sorted([ooi_class.get_ooi_type() for ooi_class in ooi_types]), self.request.GET
            )
        }

    def get_report_types_for_generate_report(self, reports: set[type[BaseReportType]]) -> list[dict[str, str]]:
        return [
            {"id": report_type.id, "name": report_type.name, "description": report_type.description}
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
        plugins = {}
        for plugin, plugin_ids in plugin_ids_dict.items():
            plugins[plugin] = [get_katalogus(self.organization.code).get_plugin(plugin_id) for plugin_id in plugin_ids]

        all_plugins_enabled = {
            plugin_type: all(plugin.enabled for plugin in plugin_list) for plugin_type, plugin_list in plugins.items()
        }

        return plugins, all_plugins_enabled

    def are_plugins_enabled(self, plugins_dict: dict[str, list[Plugin]]) -> bool:
        for k, plugins in plugins_dict.items():
            for plugin in plugins:
                if not plugin.enabled:
                    return False
        return True

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
            {"id": report_type.id, "name": report_type.name, "description": report_type.description}
            for report_type in self.get_report_types_from_choice()
        ]

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
        return redirect(reverse("generate_report_landing", kwargs=self.get_kwargs()))
