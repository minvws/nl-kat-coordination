from datetime import datetime, timezone
from typing import Any

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import urlencode
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView

from reports.report_types.aggregate_organisation_report.report import AggregateOrganisationReport
from reports.report_types.definitions import Report
from reports.report_types.helpers import get_ooi_types_from_aggregate_report
from reports.views.base import (
    REPORTS_PRE_SELECTION,
    OOISelectionView,
    ReportBreadcrumbs,
    ReportPluginView,
    ReportTypeSelectionView,
    get_selection,
)
from reports.views.mixins import SaveAggregateReportMixin
from reports.views.view_helpers import AggregateReportStepsMixin
from rocky.views.ooi_view import BaseOOIListView


class BreadcrumbsAggregateReportView(ReportBreadcrumbs):
    def build_breadcrumbs(self):
        breadcrumbs = super().build_breadcrumbs()
        kwargs = self.get_kwargs()
        selection = get_selection(self.request)
        breadcrumbs += [
            {
                "url": reverse("aggregate_report_landing", kwargs=kwargs) + selection,
                "text": _("Aggregate report"),
            },
            {
                "url": reverse("aggregate_report_select_oois", kwargs=kwargs) + selection,
                "text": _("Select objects"),
            },
            {
                "url": reverse("aggregate_report_select_report_types", kwargs=kwargs) + selection,
                "text": _("Select report types"),
            },
            {
                "url": reverse("aggregate_report_setup_scan", kwargs=kwargs) + selection,
                "text": _("Configuration"),
            },
            {
                "url": reverse("aggregate_report_export_setup", kwargs=kwargs) + selection,
                "text": _("Export setup"),
            },
            {
                "url": reverse("aggregate_report_save", kwargs=kwargs) + selection,
                "text": _("Save report"),
            },
        ]
        return breadcrumbs


class LandingAggregateReportView(BreadcrumbsAggregateReportView):
    """
    Landing page to start the 'Aggregate Report' flow.
    """

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return redirect(
            reverse("aggregate_report_select_oois", kwargs=self.get_kwargs())
            + get_selection(request, REPORTS_PRE_SELECTION)
        )


class OOISelectionAggregateReportView(
    AggregateReportStepsMixin, BreadcrumbsAggregateReportView, BaseOOIListView, OOISelectionView
):
    """
    Select Objects for the 'Aggregate Report' flow.
    """

    template_name = "aggregate_report/select_oois.html"
    breadcrumbs_step = 3
    current_step = 1
    ooi_types = get_ooi_types_from_aggregate_report(AggregateOrganisationReport)

    def post(self, request, *args, **kwargs):
        report_recipe = self.get_report_recipe()
        if not report_recipe.input_oois:
            messages.error(request, self.NONE_OOI_SELECTION_MESSAGE)
        return self.get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["channel"] = "aggregate_report"
        return context


class ReportTypesSelectionAggregateReportView(
    AggregateReportStepsMixin, BreadcrumbsAggregateReportView, OOISelectionView, ReportTypeSelectionView, TemplateView
):
    """
    Shows all possible report types from a list of Objects.
    Chooses report types for the 'Aggregate Report' flow.
    """

    template_name = "aggregate_report/select_report_types.html"
    breadcrumbs_step = 4
    current_step = 2
    ooi_types = get_ooi_types_from_aggregate_report(AggregateOrganisationReport)

    def post(self, request, *args, **kwargs):
        report_recipe = self.get_report_recipe()
        if not report_recipe.input_oois:
            messages.error(request, self.NONE_OOI_SELECTION_MESSAGE)
            return redirect(self.get_previous())
        return self.get(request, *args, **kwargs)


class SetupScanAggregateReportView(
    SaveAggregateReportMixin, AggregateReportStepsMixin, BreadcrumbsAggregateReportView, ReportPluginView, TemplateView
):
    """
    Show required and optional plugins to start scans to generate OOIs to include in report.
    """

    template_name = "aggregate_report/setup_scan.html"
    breadcrumbs_step = 5
    current_step = 3

    def post(self, request, *args, **kwargs):
        if not self.report_recipe.report_types:
            messages.error(request, self.NONE_REPORT_TYPE_SELECTION_MESSAGE)
            return redirect(self.get_previous())
        return self.get(request, *args, **kwargs)


class ExportSetupAggregateReportView(
    AggregateReportStepsMixin, BreadcrumbsAggregateReportView, ReportPluginView, TemplateView
):
    """
    Shows the export setup page where users can set their export preferences.
    """

    template_name = "aggregate_report/export_setup.html"
    breadcrumbs_step = 6
    current_step = 4

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_datetime"] = datetime.now(timezone.utc)
        context["reports"] = [_("Aggregate Report")]
        return context


class SaveAggregateReportView(SaveAggregateReportMixin, BreadcrumbsAggregateReportView, ReportPluginView):
    """
    Save the report and redirect to the saved report
    """

    template_name = "aggregate_report.html"
    breadcrumbs_step = 6
    current_step = 6
    ooi_types = get_ooi_types_from_aggregate_report(AggregateOrganisationReport)
    report_types: list[type[Report]]

    def post(self, request, *args, **kwargs):
        old_report_names = request.POST.getlist("old_report_name")
        new_report_names = request.POST.getlist("report_name")
        report_names = list(zip(old_report_names, new_report_names))
        report_ooi = self.save_report(report_names)

        return redirect(
            reverse("view_report", kwargs={"organization_code": self.organization.code})
            + "?"
            + urlencode({"report_id": report_ooi.reference})
        )
