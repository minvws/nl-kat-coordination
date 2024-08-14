from datetime import datetime, timezone
from typing import Any

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django_weasyprint import WeasyTemplateResponseMixin
from tools.view_helpers import url_with_querystring

from reports.report_types.multi_organization_report.report import MultiOrganizationReport, collect_report_data
from reports.views.base import (
    REPORTS_PRE_SELECTION,
    OOISelectionView,
    ReportBreadcrumbs,
    ReportPluginView,
    ReportTypeSelectionView,
    get_selection,
)
from reports.views.view_helpers import MultiReportStepsMixin
from rocky.views.ooi_view import BaseOOIListView


class BreadcrumbsMultiReportView(ReportBreadcrumbs):
    def build_breadcrumbs(self):
        breadcrumbs = super().build_breadcrumbs()
        kwargs = self.get_kwargs()
        selection = get_selection(self.request)
        breadcrumbs += [
            {
                "url": reverse("multi_report_landing", kwargs=kwargs) + selection,
                "text": _("Multi report"),
            },
            {
                "url": reverse("multi_report_select_oois", kwargs=kwargs) + selection,
                "text": _("Select objects"),
            },
            {
                "url": reverse("multi_report_select_report_types", kwargs=kwargs) + selection,
                "text": _("Select report types"),
            },
            {
                "url": reverse("multi_report_setup_scan", kwargs=kwargs) + selection,
                "text": _("Configuration"),
            },
            {
                "url": reverse("multi_report_export_setup", kwargs=kwargs) + selection,
                "text": _("Export setup"),
            },
            {
                "url": reverse("multi_report_view", kwargs=kwargs) + selection,
                "text": _("View report"),
            },
        ]
        return breadcrumbs


class LandingMultiReportView(BreadcrumbsMultiReportView):
    """
    Landing page to start the 'Multi Report' flow.
    """

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return redirect(
            reverse("multi_report_select_oois", kwargs=self.get_kwargs())
            + get_selection(self.request, REPORTS_PRE_SELECTION)
        )


class OOISelectionMultiReportView(MultiReportStepsMixin, BreadcrumbsMultiReportView, BaseOOIListView, OOISelectionView):
    """
    Select OOIs for the 'Multi Report' flow.
    """

    template_name = "generate_report/select_oois.html"
    breadcrumbs_step = 3
    current_step = 1
    ooi_types = MultiOrganizationReport.input_ooi_types

    def post(self, request, *args, **kwargs):
        if not self.selected_oois:
            messages.error(request, self.NONE_OOI_SELECTION_MESSAGE)
        return self.get(request, *args, **kwargs)


class ReportTypesSelectionMultiReportView(
    MultiReportStepsMixin,
    BreadcrumbsMultiReportView,
    OOISelectionView,
    ReportTypeSelectionView,
):
    """
    Shows all possible report types from a list of OOIs.
    Chooses report types for the 'Multi Report' flow.
    """

    template_name = "generate_report/select_report_types.html"
    breadcrumbs_step = 4
    current_step = 2

    def post(self, request, *args, **kwargs):
        if not self.selected_oois:
            messages.error(request, self.NONE_OOI_SELECTION_MESSAGE)
            return redirect(self.get_previous())
        return self.get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["available_report_types"] = self.get_report_types({MultiOrganizationReport})
        context["total_oois"] = self.get_total_objects()
        return context


class SetupScanMultiReportView(MultiReportStepsMixin, BreadcrumbsMultiReportView, ReportPluginView):
    """
    Show required and optional plugins to start scans to multi OOIs to include in report.
    """

    template_name = "generate_report/setup_scan.html"
    breadcrumbs_step = 5
    current_step = 3

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if self.plugins_enabled():
            return redirect(self.get_next())
        return super().get(request, *args, **kwargs)


class ExportSetupMultiReportView(MultiReportStepsMixin, BreadcrumbsMultiReportView, ReportPluginView):
    """
    Shows the export setup page where users can set their export preferences.
    """

    template_name = "generate_report/export_setup.html"
    breadcrumbs_step = 6
    current_step = 4

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if not self.selected_report_types:
            messages.error(request, _("Select at least one report type to proceed."))
            return redirect(self.get_previous())

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_datetime"] = datetime.now(timezone.utc)
        context["reports"] = [_("Multi Report")]
        return context


class MultiReportView(BreadcrumbsMultiReportView, ReportPluginView):
    """
    Shows the multi report from OOIS and report types.
    """

    template_name = "multi_report.html"
    current_step = 5

    def multi_reports_for_oois(self) -> dict[str, dict[str, Any]]:
        report = MultiOrganizationReport(self.octopoes_api_connector)

        return report.post_process_data(
            collect_report_data(self.octopoes_api_connector, self.selected_oois, self.observed_at)
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["created_at"] = datetime.now()
        context["total_oois"] = self.get_total_objects()
        context["report_types"] = [MultiOrganizationReport]
        report_data = self.multi_reports_for_oois()
        context["template"] = MultiOrganizationReport.template_path
        context["report_data"] = report_data
        context["report_download_url"] = url_with_querystring(
            reverse("multi_report_pdf", kwargs={"organization_code": self.organization.code}),
            True,
            **self.request.GET,
        )
        return context


class MultiReportPDFView(MultiReportView, WeasyTemplateResponseMixin):
    template_name = "multi_report_pdf.html"

    pdf_filename = "multi_report.pdf"
    pdf_attachment = False
    pdf_options = {
        "pdf_variant": "pdf/ua-1",
    }
