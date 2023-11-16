from typing import Any, Dict, List

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView

from octopoes.models import Reference
from reports.report_types.aggregate_organisation_report.report import AggregateOrganisationReport
from reports.report_types.helpers import (
    get_ooi_types_from_aggregate_report,
    get_plugins_for_report_ids,
    get_report_by_id,
    get_report_types_from_aggregate_report,
)
from reports.views.base import (
    BaseSelectionView,
    OOISelectionView,
    PluginSelectionView,
    ReportBreadcrumbs,
    ReportType,
    ReportTypeSelectionView,
)


class BreadcrumbsAggregateReportView(ReportBreadcrumbs):
    def build_breadcrumbs(self):
        breadcrumbs = super().build_breadcrumbs()
        kwargs = self.get_kwargs()
        selection = self.get_selection()
        breadcrumbs += [
            {
                "url": reverse("aggregate_report_landing", kwargs=kwargs) + selection,
                "text": _("Aggregate report"),
            },
            {
                "url": reverse("aggregate_report_select_oois", kwargs=kwargs) + selection,
                "text": _("Select OOIs"),
            },
            {
                "url": reverse("aggregate_report_select_report_types", kwargs=kwargs) + selection,
                "text": _("Select report types"),
            },
            {
                "url": reverse("aggregate_report_view", kwargs=kwargs) + selection,
                "text": _("View report"),
            },
        ]
        return breadcrumbs


class LandingAggregateReportView(BreadcrumbsAggregateReportView, BaseSelectionView):
    """
    Landing page to start the 'Aggregate Report' flow.
    """

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return redirect(reverse("aggregate_report_select_oois", kwargs=self.get_kwargs()))


class OOISelectionAggregateReportView(BreadcrumbsAggregateReportView, OOISelectionView):
    """
    Select OOIs for the 'Aggregate Report' flow.
    """

    template_name = "aggregate_report/select_oois.html"
    current_step = 3
    ooi_types = get_ooi_types_from_aggregate_report(AggregateOrganisationReport)


class ReportTypesSelectionAggregateReportView(BreadcrumbsAggregateReportView, ReportTypeSelectionView, TemplateView):
    """
    Shows all possible report types from a list of OOIs.
    Chooses report types for the 'Aggregate Report' flow.
    """

    template_name = "aggregate_report/select_report_types.html"
    current_step = 4
    available_report_types = get_report_types_from_aggregate_report(AggregateOrganisationReport)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["available_report_types"] = self.get_report_types_for_aggregate_report(self.available_report_types)
        return context


class SetupScanAggregateReportView(BreadcrumbsAggregateReportView, PluginSelectionView, TemplateView):
    """
    Show required and optional plugins to start scans to generate OOIs to include in report.
    """

    template_name = "aggregate_report/setup_scan.html"
    current_step = 4

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.plugins = self.get_required_optional_plugins(get_plugins_for_report_ids(self.selected_report_types))

    def get(self, request, *args, **kwargs):
        if not self.selected_report_types:
            messages.error(self.request, _("Select at least one report type to proceed."))
        return super().get(request, *args, **kwargs)


class AggregateReportView(BreadcrumbsAggregateReportView, PluginSelectionView, TemplateView):
    """
    Shows the report generated from OOIS and report types.
    """

    template_name = "generate_report.html"
    current_step = 5

    def get(self, request, *args, **kwargs):
        if not self.are_plugins_enabled():
            messages.warning(
                self.request,
                _("This report may not show all the data as some plugins are not enabled."),
            )
        return super().get(request, *args, **kwargs)

    def are_plugins_enabled(self) -> bool:
        enabled_plugins = []
        for k, plugins in self.plugins.items():
            for plugin in plugins:
                enabled_plugins.append(plugin.enabled)
        return all(enabled_plugins)

    def get_report_types_from_choice(self):
        return [get_report_by_id(report_type) for report_type in self.selected_report_types]

    def get_report_types(self) -> List[ReportType]:
        return [
            {"id": report_type.id, "name": report_type.name, "description": report_type.description}
            for report_type in self.get_report_types_from_choice()
        ]

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
