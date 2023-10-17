from logging import getLogger
from typing import Dict, List, Set, TypedDict

from django.contrib import messages
from django.urls import reverse
from django.utils.http import urlencode
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from katalogus.client import Plugin, get_katalogus
from tools.view_helpers import BreadcrumbsMixin

from octopoes.models import OOI, Reference
from reports.forms import OOITypeMultiCheckboxForReportForm
from reports.report_types.helpers import (
    get_ooi_types_with_report,
    get_plugins_for_report_ids,
    get_report_by_id,
    get_report_types_for_oois,
)
from rocky.views.mixins import OctopoesView
from rocky.views.ooi_view import BaseOOIListView

logger = getLogger(__name__)


class ReportType(TypedDict):
    id: str
    name: str
    description: str


class ReportBreadcrumbs(BreadcrumbsMixin):
    current_step: int = 0

    def build_breadcrumbs(self):
        kwargs = {"organization_code": self.organization.code}
        selection = "?" + urlencode(self.request.GET, True)

        breadcrumbs = [
            {
                "url": reverse("report_oois_selection", kwargs=kwargs) + selection,
                "text": _("Reports"),
            },
            {
                "url": reverse("report_types_selection", kwargs=kwargs) + selection,
                "text": _("Choose report types"),
            },
            {
                "url": reverse("report_setup_scan", kwargs=kwargs) + selection,
                "text": _("Set up scan"),
            },
            {
                "url": reverse("report_view", kwargs=kwargs) + selection,
                "text": _("View Report"),
            },
        ]

        return breadcrumbs[: self.current_step]


class BaseReportView(ReportBreadcrumbs, OctopoesView):
    ooi_types = get_ooi_types_with_report()

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.valid_time = self.get_observed_at()
        self.selected_oois = request.GET.getlist("ooi", [])
        self.yielded_report_types = get_report_types_for_oois(self.selected_oois)
        self.selected_report_types = request.GET.getlist("report_type", [])

    def get_oois(self) -> List[OOI]:
        return [self.get_single_ooi(ooi_id) for ooi_id in self.selected_oois]

    def get_report_types_from_choice(self):
        return [get_report_by_id(report_type) for report_type in self.selected_report_types]

    def get_report_types(self) -> List[ReportType]:
        return [
            {"id": report_type.id, "name": report_type.name, "description": report_type.description}
            for report_type in self.get_report_types_from_choice()
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["observed_at"] = self.valid_time
        context["ooi_type_form"] = OOITypeMultiCheckboxForReportForm(self.request.GET)
        context["selected_oois"] = self.selected_oois
        context["selected_report_types"] = self.selected_report_types
        return context


class BaseSelectionView(BaseReportView):
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.oois = self.get_oois()
        self.report_types_choices = self.get_report_types_from_ooi_selection()

    def get_report_types_from_ooi_selection(self) -> List[ReportType]:
        return [
            {"id": report_type.id, "name": report_type.name, "description": report_type.description}
            for report_type in self.yielded_report_types
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["oois"] = self.oois
        context["report_types_choices"] = self.report_types_choices
        return context


class PluginSelectionView(BaseReportView):
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.plugin_ids = get_plugins_for_report_ids(self.selected_report_types)
        self.plugins = self.get_required_optional_plugins(self.plugin_ids)

    def get_required_optional_plugins(self, plugin_ids: Dict[str, Set[str]]) -> Dict[str, Plugin]:
        plugins = {}
        for plugin, plugin_ids in plugin_ids.items():
            plugins[plugin] = [get_katalogus(self.organization.code).get_plugin(plugin_id) for plugin_id in plugin_ids]
        return plugins

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["plugins"] = self.plugins
        return context


class ReportOOISelectionView(BaseReportView, BaseOOIListView):
    """
    Select OOIs from list to include in report.
    """

    template_name = "report_oois_selection.html"
    current_step = 1


class ReportTypeSelectionView(BaseSelectionView, TemplateView):
    """
    Shows all possible report types from a list of OOIs.
    Chooses report types to generate a report.
    """

    template_name = "report_types_selection.html"
    current_step = 2

    def get(self, request, *args, **kwargs):
        if not self.selected_oois:
            messages.add_message(self.request, messages.ERROR, _("Select at least one OOI to proceed."))
        return super().get(request, *args, **kwargs)


class ReportSetupScanView(PluginSelectionView, TemplateView):
    """
    Show required and optional plugins to start scans to generate OOIs to include in report.
    """

    template_name = "report_setup_scan.html"
    current_step = 3

    def get(self, request, *args, **kwargs):
        if not self.selected_report_types:
            messages.add_message(self.request, messages.ERROR, _("Select at least one report type to proceed."))
        return super().get(request, *args, **kwargs)


class ReportView(BaseSelectionView, PluginSelectionView, TemplateView):
    """
    Shows the report generated from OOIS and report types.
    """

    template_name = "report.html"
    current_step = 4

    def get(self, request, *args, **kwargs):
        if not self.are_plugins_enabled():
            messages.add_message(
                self.request,
                messages.WARNING,
                _("This report may not show all the data as some plugins are not enabled."),
            )
        return super().get(request, *args, **kwargs)

    def are_plugins_enabled(self) -> bool:
        enabled_plugins = []
        for k, plugins in self.plugins.items():
            for plugin in plugins:
                enabled_plugins.append(plugin.enabled)
        return all(enabled_plugins)

    def generate_reports_for_oois(self) -> Dict[str, Dict[str, Dict[str, str]]]:
        report_data = {}
        for ooi in self.selected_oois:
            report_data[ooi] = {}
            for report_type in self.get_report_types_from_choice():
                if Reference.from_str(ooi).class_type in report_type.input_ooi_types:
                    report = report_type(self.octopoes_api_connector)
                    data = report.generate_data(ooi, valid_time=self.valid_time)
                    template = report.template_path
                    report_data[ooi][report_type.name] = {"data": data, "template": template}
        return report_data

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["report_types"] = self.get_report_types()
        context["report_data"] = self.generate_reports_for_oois()
        return context
