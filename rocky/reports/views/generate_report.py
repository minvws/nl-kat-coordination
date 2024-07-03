from typing import Any

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import urlencode
from django.utils.translation import gettext_lazy as _

from reports.report_types.helpers import get_ooi_types_with_report, get_report_types_for_oois
from reports.views.base import (
    REPORTS_PRE_SELECTION,
    OOISelectionView,
    ReportBreadcrumbs,
    ReportPluginView,
    ReportTypeSelectionView,
    get_selection,
)
from reports.views.mixins import SaveGenerateReportMixin
from reports.views.view_helpers import GenerateReportStepsMixin
from rocky.views.ooi_view import BaseOOIListView


class BreadcrumbsGenerateReportView(ReportBreadcrumbs):
    def build_breadcrumbs(self):
        breadcrumbs = super().build_breadcrumbs()
        kwargs = self.get_kwargs()
        selection = get_selection(self.request)
        breadcrumbs += [
            {
                "url": reverse("generate_report_landing", kwargs=kwargs) + selection,
                "text": _("Generate report"),
            },
            {
                "url": reverse("generate_report_select_oois", kwargs=kwargs) + selection,
                "text": _("Select Objects"),
            },
            {
                "url": reverse("generate_report_select_report_types", kwargs=kwargs) + selection,
                "text": _("Select report types"),
            },
            {
                "url": reverse("generate_report_setup_scan", kwargs=kwargs) + selection,
                "text": _("Configuration"),
            },
            {
                "url": reverse("generate_report_view", kwargs=kwargs) + selection,
                "text": _("Save report"),
            },
        ]
        return breadcrumbs


class LandingGenerateReportView(BreadcrumbsGenerateReportView):
    """
    Landing page to start the 'Generate Report' flow.
    """

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return redirect(
            reverse("generate_report_select_oois", kwargs=self.get_kwargs())
            + get_selection(request, REPORTS_PRE_SELECTION)
        )


class OOISelectionGenerateReportView(
    GenerateReportStepsMixin, BreadcrumbsGenerateReportView, BaseOOIListView, OOISelectionView
):
    """
    Select objects for the 'Generate Report' flow.
    """

    template_name = "generate_report/select_oois.html"
    breadcrumbs_step = 3
    current_step = 1
    ooi_types = get_ooi_types_with_report()

    def post(self, request, *args, **kwargs):
        self.ooi_selection_is_valid()
        return self.get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["channel"] = "generate_report"
        return context


class ReportTypesSelectionGenerateReportView(
    GenerateReportStepsMixin, BreadcrumbsGenerateReportView, OOISelectionView, ReportTypeSelectionView
):
    """
    Shows all possible report types from a list of OOIs.
    Chooses report types for the 'Generate Report' flow.
    """

    template_name = "generate_report/select_report_types.html"
    breadcrumbs_step = 4
    current_step = 2

    def post(self, request, *args, **kwargs):
        if not self.ooi_selection_is_valid():
            return redirect(self.get_previous())
        return self.get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["available_report_types"] = self.get_report_types(get_report_types_for_oois(self.get_oois_pk()))
        context["total_oois"] = self.get_total_objects()
        return context


class SetupScanGenerateReportView(
    SaveGenerateReportMixin,
    GenerateReportStepsMixin,
    BreadcrumbsGenerateReportView,
    ReportPluginView,
):
    """
    Show required and optional plugins to start scans to generate OOIs to include in report.
    """

    template_name = "generate_report/setup_scan.html"
    breadcrumbs_step = 5
    current_step = 3

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if not self.report_has_required_plugins() or self.plugins_enabled():
            report_ooi = self.save_report()
            return redirect(
                reverse("view_report", kwargs={"organization_code": self.organization.code})
                + "?"
                + urlencode({"report_id": report_ooi.reference})
            )
        if not self.plugins:
            return redirect(self.get_previous())
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if not self.report_type_selection_is_valid():
            return redirect(self.get_previous())
        return self.get(request, *args, **kwargs)


class SaveGenerateReportView(SaveGenerateReportMixin, BreadcrumbsGenerateReportView, ReportPluginView):
    """
    Save the report generated.
    """

    template_name = "generate_report.html"
    breadcrumbs_step = 6
    current_step = 4

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        report_ooi = self.save_report()

        return redirect(
            reverse("view_report", kwargs={"organization_code": self.organization.code})
            + "?"
            + urlencode({"report_id": report_ooi.reference})
        )
