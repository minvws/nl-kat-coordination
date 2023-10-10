from logging import getLogger
from typing import Any, Dict, List

from django.contrib import messages
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from katalogus.client import Plugin, get_katalogus
from tools.view_helpers import BreadcrumbsMixin

from octopoes.models import OOI
from reports.forms import OOITypeMultiCheckboxForReportForm
from reports.report_types.helpers import (
    generate_reports_for_oois,
    get_ooi_types_with_report,
    get_plugins_for_report_ids,
    get_report_types_for_oois,
)
from rocky.views.mixins import OctopoesView
from rocky.views.ooi_view import BaseOOIListView

logger = getLogger(__name__)


class ReportBreadcrumbs(BreadcrumbsMixin):
    current_step: int = 0

    def build_breadcrumbs(self):
        kwargs = {"organization_code": self.organization.code}
        breadcrumbs = [
            {
                "url": reverse("report_oois_selection", kwargs=kwargs),
                "text": _("Reports"),
            },
            {
                "url": reverse("report_types_selection", kwargs=kwargs),
                "text": _("Choose report types"),
            },
            {
                "url": reverse("report_setup_scan", kwargs=kwargs),
                "text": _("Set up scan"),
            },
            {
                "url": reverse("report_view", kwargs=kwargs),
                "text": _("View Report"),
            },
        ]

        return breadcrumbs[: self.current_step]


class BaseReportView(ReportBreadcrumbs, OctopoesView):
    ooi_types = get_ooi_types_with_report()

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.valid_time = self.get_observed_at()
        self.oois_selection = request.GET.getlist("ooi", [])
        self.report_types_selection = request.GET.getlist("report_type", [])

    def get_report_types_from_oois_selection(self, ooi_ids: List[str]) -> List[Dict[str, str]]:
        return [
            {"id": report_type.id, "name": report_type.name, "description": report_type.description}
            for report_type in get_report_types_for_oois(ooi_ids)
        ]

    def get_oois_from_selection(self, ooi_ids: List[str]):
        return [self.get_single_ooi(ooi) for ooi in ooi_ids]

    def get_reports_data(self) -> Dict[str, Any]:
        report_data = {}
        if self.oois_selection and self.report_types_selection:
            report_data = generate_reports_for_oois(
                self.oois_selection, self.report_types_selection, self.octopoes_api_connector
            )
        return report_data

    def get_required_optional_plugins(self, report_type_ids: List[str]) -> Dict[str, Plugin]:
        katalogus_client = get_katalogus(self.organization.code)
        plugins = get_plugins_for_report_ids(report_type_ids)
        for plugin, value in plugins.items():
            plugins[plugin] = [katalogus_client.get_plugin(plugin_id) for plugin_id in value]
        return plugins

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["observed_at"] = self.valid_time
        context["ooi_type_form"] = OOITypeMultiCheckboxForReportForm(self.request.GET)
        context["oois_selection"] = self.oois_selection
        context["report_types_selection"] = self.report_types_selection
        return context


class BaseSelectionView(BaseReportView):
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.oois = self.get_oois_from_selection(self.oois_selection)
        self.report_types = self.get_report_types_from_oois_selection(self.oois_selection)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["oois"] = self.oois
        context["report_types"] = self.report_types
        return context


class PluginSelectionView(BaseReportView):
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.plugins = self.get_required_optional_plugins(self.report_types_selection)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["plugins"] = self.plugins
        return context

    def are_plugins_enabled(self) -> bool:
        enabled_plugins = []
        for plugin_key, plugins_to_scan in self.plugins.items():
            for plugin in plugins_to_scan:
                enabled_plugins.append(plugin.enabled)
        return all(enabled_plugins)

    def get_max_scan_level_plugins(self):
        scan_levels = []
        for plugin_key, plugins_to_scan in self.plugins.items():
            for plugin in plugins_to_scan:
                scan_levels.append(plugin.scan_level.value)
        return max(scan_levels)

    def oois_not_enough_clearance(self, oois: List[OOI]):
        plugins_max_scan_level = self.get_max_scan_level_plugins()
        return all([ooi.scan_profile.level.value >= plugins_max_scan_level for ooi in oois])


class ReportOOISelectionView(BaseReportView, BaseOOIListView):
    """
    Select OOIs from list to include in report.
    """

    template_name = "report_oois_selection.html"
    current_step = 1
    paginate_by = 500


class ReportTypeSelectionView(BaseSelectionView, TemplateView):
    """
    Shows all possible report types from a list of OOIs.
    Chooses report types to generate a report.
    """

    template_name = "report_types_selection.html"
    current_step = 2

    def get(self, request, *args, **kwargs):
        if not self.oois_selection:
            messages.add_message(self.request, messages.ERROR, _("Select at least one OOI to proceed."))
        return super().get(request, *args, **kwargs)


class ReportSetupScanView(PluginSelectionView, TemplateView):
    """
    Show required and optional plugins to start scans to generate OOIs to include in report.
    """

    template_name = "report_setup_scan.html"
    current_step = 3

    def get(self, request, *args, **kwargs):
        if not self.report_types_selection:
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
                _("This report may not show all the data as some plugins are not enabled. "),
            )
        if not self.oois_not_enough_clearance(self.oois):
            messages.add_message(
                self.request,
                messages.WARNING,
                _("Some plugins are not able to scan due that they do not match object's clearance level."),
            )
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["report_data"] = self.get_reports_data()
        return context
