from typing import Any

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from django_weasyprint import WeasyTemplateResponseMixin
from tools.view_helpers import url_with_querystring

from reports.report_types.multi_organization_report.report import MultiOrganizationReport, collect_report_data
from reports.views.base import REPORTS_PRE_SELECTION, BaseReportView, ReportBreadcrumbs, get_selection
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
                "text": _("Select OOIs"),
            },
            {
                "url": reverse("multi_report_select_report_types", kwargs=kwargs) + selection,
                "text": _("Select report types"),
            },
            {
                "url": reverse("multi_report_setup_scan", kwargs=kwargs) + selection,
                "text": _("Setup scan"),
            },
            {
                "url": reverse("multi_report_view", kwargs=kwargs) + selection,
                "text": _("View report"),
            },
        ]
        return breadcrumbs


class LandingMultiReportView(BreadcrumbsMultiReportView, BaseReportView):
    """
    Landing page to start the 'Multi Report' flow.
    """

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return redirect(
            reverse("multi_report_select_oois", kwargs=self.get_kwargs())
            + get_selection(self.request, REPORTS_PRE_SELECTION)
        )


class OOISelectionMultiReportView(BreadcrumbsMultiReportView, BaseReportView, BaseOOIListView):
    """
    Select OOIs for the 'Multi Report' flow.
    """

    template_name = "generate_report/select_oois.html"
    current_step = 3
    ooi_types = MultiOrganizationReport.input_ooi_types

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_ooi_filter_forms(self.ooi_types))
        return context


class ReportTypesSelectionMultiReportView(BreadcrumbsMultiReportView, BaseReportView, TemplateView):
    """
    Shows all possible report types from a list of OOIs.
    Chooses report types for the 'Multi Report' flow.
    """

    template_name = "generate_report/select_report_types.html"
    current_step = 4

    def get(self, request, *args, **kwargs):
        if not self.selected_oois:
            messages.error(self.request, _("Select at least one OOI to proceed."))
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["oois"] = self.get_oois()
        context["available_report_types"] = self.get_report_types_for_generate_report([MultiOrganizationReport])
        return context


class SetupScanMultiReportView(BreadcrumbsMultiReportView, BaseReportView, TemplateView):
    """
    Show required and optional plugins to start scans to multi OOIs to include in report.
    """

    template_name = "generate_report/setup_scan.html"
    current_step = 5

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if not self.selected_report_types:
            messages.error(self.request, _("Select at least one report type to proceed."))

        if self.all_plugins_enabled["required"] and self.all_plugins_enabled["optional"]:
            return redirect(reverse("multi_report_view", kwargs=kwargs) + get_selection(request))

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["plugins"] = {"required": [], "optional": []}
        return context


class MultiReportView(BreadcrumbsMultiReportView, BaseReportView, TemplateView):
    """
    Shows the multi report from OOIS and report types.
    """

    template_name = "multi_report.html"
    current_step = 6

    def multi_reports_for_oois(self) -> dict[str, dict[str, Any]]:
        report = MultiOrganizationReport(self.octopoes_api_connector)

        return report.post_process_data(collect_report_data(self.octopoes_api_connector, self.selected_oois))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["oois"] = self.get_oois()
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
