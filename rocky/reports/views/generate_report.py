from datetime import datetime, timezone
from typing import Any

from django.contrib import messages
from django.core.exceptions import SuspiciousOperation
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import urlencode
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from tools.view_helpers import PostRedirect

from octopoes.models import OOI
from reports.report_types.definitions import BaseReport
from reports.report_types.helpers import get_ooi_types_with_report
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
                "text": _("Select objects"),
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
                "url": reverse("generate_report_export_setup", kwargs=kwargs) + selection,
                "text": _("Export setup"),
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
        if not self.get_ooi_selection():
            messages.error(request, self.NONE_OOI_SELECTION_MESSAGE)
        return self.get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["channel"] = "generate_report"
        return context


class ReportTypesSelectionGenerateReportView(
    GenerateReportStepsMixin, BreadcrumbsGenerateReportView, OOISelectionView, ReportTypeSelectionView, TemplateView
):
    """
    Shows all possible report types from a list of OOIs.
    Chooses report types for the 'Generate Report' flow.
    """

    template_name = "generate_report/select_report_types.html"
    breadcrumbs_step = 4
    current_step = 2

    def post(self, request, *args, **kwargs):
        if not self.get_ooi_selection():
            messages.error(request, self.NONE_OOI_SELECTION_MESSAGE)
            return PostRedirect(self.get_previous())
        return self.get(request, *args, **kwargs)


class SetupScanGenerateReportView(
    SaveGenerateReportMixin, GenerateReportStepsMixin, BreadcrumbsGenerateReportView, ReportPluginView, TemplateView
):
    """
    Show required and optional plugins to start scans to generate OOIs to include in report.
    """

    template_name = "generate_report/setup_scan.html"
    breadcrumbs_step = 5
    current_step = 3

    def post(self, request, *args, **kwargs):
        if not self.report_recipe.report_types:
            messages.error(request, self.NONE_REPORT_TYPE_SELECTION_MESSAGE)
            return PostRedirect(self.get_previous())

        if "return" in self.request.POST and self.plugins_enabled():
            return PostRedirect(self.get_previous())

        if self.plugins_enabled():
            return PostRedirect(self.get_next())
        return self.get(request, *args, **kwargs)


class ExportSetupGenerateReportView(
    GenerateReportStepsMixin, BreadcrumbsGenerateReportView, ReportPluginView, TemplateView
):
    """
    Shows the export setup page where users can set their export preferences.
    """

    template_name = "generate_report/export_setup.html"
    breadcrumbs_step = 6
    current_step = 4
    reports: dict[str, str] = {}

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if not self.report_recipe.report_types:
            messages.error(request, self.NONE_REPORT_TYPE_SELECTION_MESSAGE)
            return PostRedirect(self.get_previous())
        oois = list(self.get_oois())
        report_types = list(self.get_report_types())
        self.reports = create_report_names(oois, report_types)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["reports"] = self.reports
        context["current_datetime"] = datetime.now(timezone.utc)
        return context


class SaveGenerateReportView(SaveGenerateReportMixin, BreadcrumbsGenerateReportView, ReportPluginView):
    """
    Save the report generated.
    """

    template_name = "generate_report.html"
    breadcrumbs_step = 6
    current_step = 4

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        old_report_names = request.POST.getlist("old_report_name")
        report_names = request.POST.getlist("report_name")
        reference_dates = request.POST.getlist("reference_date")

        if "" in report_names:
            raise SuspiciousOperation(_("Empty name should not be possible."))
        else:
            final_report_names = list(zip(old_report_names, self.finalise_report_names(report_names, reference_dates)))
            report_ooi = self.save_report(final_report_names)

            return redirect(
                reverse("view_report", kwargs={"organization_code": self.organization.code})
                + "?"
                + urlencode({"report_id": report_ooi.reference})
            )


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
            name = _("{report_type} for {oois_count} objects").format(report_type=report_type, oois_count=oois_count)
        reports[name] = ""

    # Create name for subreports or single reports
    for ooi in oois:
        for report_type_ in report_types:
            name = _("{report_type} for {ooi}").format(report_type=report_type_.name, ooi=ooi.human_readable)
            reports[name] = ""

    return reports
