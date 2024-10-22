from datetime import datetime
from typing import Any

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
    ReportFinalSettingsView,
    ReportPluginView,
    ReportTypeSelectionView,
    get_selection,
)
from reports.views.view_helpers import MultiReportStepsMixin


class BreadcrumbsMultiReportView(ReportBreadcrumbs):
    def build_breadcrumbs(self):
        breadcrumbs = super().build_breadcrumbs()
        kwargs = self.get_kwargs()
        selection = get_selection(self.request)
        breadcrumbs += [
            {"url": reverse("multi_report_landing", kwargs=kwargs) + selection, "text": _("Multi report")},
            {"url": reverse("multi_report_select_oois", kwargs=kwargs) + selection, "text": _("Select objects")},
            {
                "url": reverse("multi_report_select_report_types", kwargs=kwargs) + selection,
                "text": _("Select report types"),
            },
            {"url": reverse("multi_report_setup_scan", kwargs=kwargs) + selection, "text": _("Configuration")},
            {"url": reverse("multi_report_export_setup", kwargs=kwargs) + selection, "text": _("Export setup")},
            {"url": reverse("multi_report_view", kwargs=kwargs) + selection, "text": _("View report")},
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


class OOISelectionMultiReportView(MultiReportStepsMixin, BreadcrumbsMultiReportView, OOISelectionView):
    """
    Select OOIs for the 'Multi Report' flow.
    """

    template_name = "generate_report/select_oois.html"
    breadcrumbs_step = 3
    current_step = 1
    ooi_types = MultiOrganizationReport.input_ooi_types


class ReportTypesSelectionMultiReportView(
    MultiReportStepsMixin, BreadcrumbsMultiReportView, OOISelectionView, ReportTypeSelectionView
):
    """
    Shows all possible report types from a list of OOIs.
    Chooses report types for the 'Multi Report' flow.
    """

    template_name = "generate_report/select_report_types.html"
    breadcrumbs_step = 4
    current_step = 2
    report_type = MultiOrganizationReport
    ooi_types = MultiOrganizationReport.input_ooi_types


class SetupScanMultiReportView(MultiReportStepsMixin, BreadcrumbsMultiReportView, ReportPluginView):
    """
    Show required and optional plugins to start scans to multi OOIs to include in report.
    """

    template_name = "generate_report/setup_scan.html"
    breadcrumbs_step = 5
    current_step = 3
    ooi_types = MultiOrganizationReport.input_ooi_types


class ExportSetupMultiReportView(MultiReportStepsMixin, BreadcrumbsMultiReportView, ReportFinalSettingsView):
    """
    Shows the export setup page where users can set their export preferences.
    """

    template_name = "generate_report/export_setup.html"
    breadcrumbs_step = 6
    current_step = 4
    report_type = MultiOrganizationReport
    ooi_types = MultiOrganizationReport.input_ooi_types


class MultiReportView(BreadcrumbsMultiReportView, ReportPluginView):
    """
    Shows the multi report from OOIS and report types.
    """

    template_name = "multi_report.html"
    current_step = 5
    ooi_types = MultiOrganizationReport.input_ooi_types

    def multi_reports_for_oois(self) -> dict[str, dict[str, Any]]:
        report = MultiOrganizationReport(self.octopoes_api_connector)

        return report.post_process_data(
            collect_report_data(self.octopoes_api_connector, self.get_ooi_pks(), self.observed_at)
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["created_at"] = datetime.now()
        context["total_oois"] = len(self.get_ooi_pks())
        context["report_types"] = [MultiOrganizationReport]
        context["template"] = MultiOrganizationReport.template_path
        context["report_data"] = self.multi_reports_for_oois()
        context["report_download_url"] = url_with_querystring(
            reverse("multi_report_pdf", kwargs={"organization_code": self.organization.code}), True, **self.request.GET
        )
        return context


class MultiReportPDFView(MultiReportView, WeasyTemplateResponseMixin):
    template_name = "multi_report_pdf.html"

    pdf_filename = "multi_report.pdf"
    pdf_attachment = False
    pdf_options = {"pdf_variant": "pdf/ua-1"}
