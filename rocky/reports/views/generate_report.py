import logging
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from django_weasyprint import WeasyTemplateResponseMixin
from tools.view_helpers import url_with_querystring

from octopoes.models import Reference
from octopoes.models.exception import ObjectNotFoundException, TypeNotFound
from reports.report_types.concatenated_report.report import ConcatenatedReport
from reports.report_types.definitions import Report
from reports.report_types.helpers import REPORTS, get_ooi_types_with_report, get_report_by_id, get_report_types_for_oois
from reports.views.base import (
    REPORTS_PRE_SELECTION,
    ReportBreadcrumbs,
    ReportOOIView,
    ReportPluginView,
    ReportTypeView,
    get_selection,
)
from reports.views.view_helpers import GenerateReportStepsMixin
from rocky.views.ooi_view import BaseOOIListView

logger = logging.getLogger(__name__)


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
                "text": _("View report"),
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
    GenerateReportStepsMixin,
    BreadcrumbsGenerateReportView,
    ReportOOIView,
    BaseOOIListView,
):
    """
    Select objects for the 'Generate Report' flow.
    """

    template_name = "generate_report/select_oois.html"
    breadcrumbs_step = 3
    current_step = 1
    ooi_types = get_ooi_types_with_report()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["channel"] = "generate_report"
        context.update(self.get_ooi_filter_forms(self.ooi_types))
        return context


class ReportTypesSelectionGenerateReportView(
    GenerateReportStepsMixin,
    BreadcrumbsGenerateReportView,
    ReportOOIView,
    ReportTypeView,
    TemplateView,
):
    """
    Shows all possible report types from a list of OOIs.
    Chooses report types for the 'Generate Report' flow.
    """

    template_name = "generate_report/select_report_types.html"
    breadcrumbs_step = 4
    current_step = 2

    def get(self, request, *args, **kwargs):
        if not self.selected_oois:
            messages.error(self.request, _("Select at least one OOI to proceed."))
            return redirect(self.get_previous())
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["available_report_types"] = self.get_report_types(get_report_types_for_oois(self.selected_oois))
        return context


class SetupScanGenerateReportView(
    GenerateReportStepsMixin,
    BreadcrumbsGenerateReportView,
    ReportPluginView,
    TemplateView,
):
    """
    Show required and optional plugins to start scans to generate OOIs to include in report.
    """

    template_name = "generate_report/setup_scan.html"
    breadcrumbs_step = 5
    current_step = 3

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if not self.report_has_required_plugins():
            return redirect(self.get_next())
        if not self.plugins:
            return redirect(self.get_previous())
        if self.plugins_enabled():
            return redirect(self.get_next())
        return super().get(request, *args, **kwargs)


class GenerateReportView(BreadcrumbsGenerateReportView, ReportPluginView, TemplateView):
    """
    Shows the report generated from OOIS and report types.
    """

    template_name = "generate_report.html"
    breadcrumbs_step = 6
    current_step = 6
    report_types: Sequence[type[Report]]

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if not self.selected_report_types:
            messages.error(request, _("Select at least one report type to proceed."))
            return redirect(
                reverse("generate_report_select_report_types", kwargs=self.get_kwargs()) + get_selection(request)
            )
        return super().get(request, *args, **kwargs)

    def generate_reports_for_oois(self) -> dict[str, dict[str, dict[str, Any]]]:
        error_reports = []
        report_data: dict[str, dict[str, dict[str, Any]]] = {}
        by_type: dict[str, list[str]] = {}

        number_of_reports = 0
        for ooi in self.selected_oois:
            ooi_type = Reference.from_str(ooi).class_

            if ooi_type not in by_type:
                by_type[ooi_type] = []

            by_type[ooi_type].append(ooi)

        sorted_report_types = list(filter(lambda x: x in self.report_types, REPORTS))
        for report_type in sorted_report_types:
            oois = {
                ooi for ooi_type in report_type.input_ooi_types for ooi in by_type.get(ooi_type.get_object_type(), [])
            }

            try:
                results = report_type(self.octopoes_api_connector).collect_data(oois, self.observed_at)
            except ObjectNotFoundException:
                error_reports.append(report_type.id)
                continue
            except TypeNotFound:
                error_reports.append(report_type.id)
                continue

            for ooi, data in results.items():
                if report_type.id not in report_data:
                    report_data[report_type.id] = {}

                report_data[report_type.id][ooi] = {
                    "data": data,
                    "template": report_type.template_path,
                    "report_name": report_type.name,
                }
                number_of_reports += 1

        observed_at = self.get_observed_at()

        # if its not a single report, we need a parent
        if number_of_reports > 1:
            parent_report_ooi = self.save_report(
                data={},
                report_type=ConcatenatedReport,
                input_ooi=None,
                parent=None,
                has_parent=False,
                observed_at=observed_at,
            )
            for report_type, ooi_data in report_data.items():
                for ooi, data in ooi_data.items():
                    self.save_report(
                        data=data["data"],
                        report_type=get_report_by_id(report_type),
                        input_ooi=Reference.from_str(ooi),
                        parent=parent_report_ooi.reference,
                        has_parent=True,
                        observed_at=observed_at,
                    )
        # if its a single report we can just save it as complete
        else:
            report_type = next(iter(report_data))
            ooi = next(iter(report_data[report_type]))
            data = report_data[report_type][ooi]
            self.save_report(
                data=data["data"],
                report_type=get_report_by_id(report_type),
                input_ooi=Reference.from_str(ooi),
                parent=None,
                has_parent=False,
                observed_at=observed_at,
            )
        # If OOI could not be found or the date is incorrect, it will be shown to the user as a message error
        if error_reports:
            report_types = ", ".join(set(error_reports))
            date = self.observed_at.date()
            error_message = _("No data could be found for %(report_types). Object(s) did not exist on %(date)s.") % {
                "report_types": report_types,
                "date": date,
            }
            messages.error(self.request, error_message)

        return report_data

    def get_observed_at(self):
        return self.observed_at if self.observed_at < datetime.now(timezone.utc) else datetime.now(timezone.utc)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["created_at"] = datetime.now()
        context["report_data"] = self.generate_reports_for_oois()
        context["report_types"] = [report.class_attributes() for report in self.report_types]
        context["report_download_url"] = url_with_querystring(
            reverse(
                "generate_report_pdf",
                kwargs={"organization_code": self.organization.code},
            ),
            True,
            **self.request.GET,
        )
        return context


class GenerateReportPDFView(GenerateReportView, WeasyTemplateResponseMixin):
    template_name = "generate_report_pdf.html"

    pdf_filename = "generate_report.pdf"
    pdf_attachment = False
    pdf_options = {
        "pdf_variant": "pdf/ua-1",
    }
