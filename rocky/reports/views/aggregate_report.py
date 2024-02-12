from typing import Any, Dict, Tuple

from django.conf import settings
from django.contrib import messages
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from django_weasyprint import WeasyTemplateResponseMixin
from tools.view_helpers import url_with_querystring

from reports.report_types.aggregate_organisation_report.report import AggregateOrganisationReport, aggregate_reports
from reports.report_types.helpers import (
    get_ooi_types_from_aggregate_report,
    get_plugins_for_report_ids,
    get_report_types_from_aggregate_report,
)
from reports.utils import JSONEncoder, debug_json_keys
from reports.views.base import REPORTS_PRE_SELECTION, BaseReportView, ReportBreadcrumbs, get_selection
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
                "text": _("Select Objects"),
            },
            {
                "url": reverse("aggregate_report_select_report_types", kwargs=kwargs) + selection,
                "text": _("Select report types"),
            },
            {
                "url": reverse("aggregate_report_setup_scan", kwargs=kwargs) + selection,
                "text": _("Setup scan"),
            },
            {
                "url": reverse("aggregate_report_view", kwargs=kwargs) + selection,
                "text": _("View report"),
            },
        ]
        return breadcrumbs


class LandingAggregateReportView(BreadcrumbsAggregateReportView, BaseReportView):
    """
    Landing page to start the 'Aggregate Report' flow.
    """

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return redirect(
            reverse("aggregate_report_select_oois", kwargs=self.get_kwargs())
            + get_selection(request, REPORTS_PRE_SELECTION)
        )


class OOISelectionAggregateReportView(BreadcrumbsAggregateReportView, BaseOOIListView, BaseReportView):
    """
    Select Objects for the 'Aggregate Report' flow.
    """

    template_name = "aggregate_report/select_oois.html"
    current_step = 3
    ooi_types = get_ooi_types_from_aggregate_report(AggregateOrganisationReport)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_ooi_filter_forms(self.ooi_types))
        context["channel"] = "aggregate_report"
        return context


class ReportTypesSelectionAggregateReportView(BreadcrumbsAggregateReportView, BaseReportView, TemplateView):
    """
    Shows all possible report types from a list of Objects.
    Chooses report types for the 'Aggregate Report' flow.
    """

    template_name = "aggregate_report/select_report_types.html"
    current_step = 4

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.available_report_types = self.get_report_types_for_aggregate_report(
            get_report_types_from_aggregate_report(AggregateOrganisationReport)
        )

    def get(self, request, *args, **kwargs):
        if not self.selected_oois:
            messages.error(self.request, _("Select at least one OOI to proceed."))
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if "all" not in self.selected_oois:
            context["oois"] = self.get_oois()
        else:
            context["oois"] = "all"
        context["available_report_types_aggregate"] = self.available_report_types
        context["count_available_report_types_aggregate"] = len(self.available_report_types["required"]) + len(
            self.available_report_types["optional"]
        )
        return context


class SetupScanAggregateReportView(BreadcrumbsAggregateReportView, BaseReportView, TemplateView):
    """
    Show required and optional plugins to start scans to generate OOIs to include in report.
    """

    template_name = "aggregate_report/setup_scan.html"
    current_step = 5

    def get(self, request, *args, **kwargs):
        if not self.selected_report_types:
            messages.error(self.request, _("Select at least one report type to proceed."))
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["plugins"] = self.get_required_optional_plugins(get_plugins_for_report_ids(self.selected_report_types))
        return context


class AggregateReportView(BreadcrumbsAggregateReportView, BaseReportView, TemplateView):
    """
    Shows the report generated from OOIS and report types.
    """

    template_name = "aggregate_report.html"
    current_step = 6
    ooi_types = get_ooi_types_from_aggregate_report(AggregateOrganisationReport)

    def get(self, request, *args, **kwargs):
        if "json" in self.request.GET and self.request.GET["json"] == "true":
            aggregate_report, post_processed_data, report_data = self.generate_reports_for_oois()

            response = {
                "organization_code": self.organization.code,
                "organization_name": self.organization.name,
                "organization_tags": list(self.organization.tags.all()),
                "data": {
                    "report_data": report_data,
                    "post_processed_data": post_processed_data,
                },
            }

            try:
                response = JsonResponse(response, encoder=JSONEncoder)
            except TypeError:
                # We can't use translated strings as keys in JSON. This
                # debugging code makes it easy to spot where the problem is.
                if settings.DEBUG:
                    debug_json_keys(report_data, [])
                    debug_json_keys(post_processed_data, [])
                raise
            else:
                response["Content-Disposition"] = f"attachment; filename=report-{self.organization.code}.json"
                return response

        return super().get(request, *args, **kwargs)

    def generate_reports_for_oois(self) -> Tuple[AggregateOrganisationReport, Any, Dict[Any, Dict[Any, Any]]]:
        aggregate_report, post_processed_data, report_data, error_oois = aggregate_reports(
            self.octopoes_api_connector, self.get_oois(), self.selected_report_types, self.observed_at
        )

        # If OOI could not be found or the date is incorrect, it will be shown to the user as a message error
        if error_oois:
            oois = ", ".join(set(error_oois))
            date = self.observed_at.date()
            error_message = _("No data could be found for %(oois)s. Object(s) did not exist on %(date)s.") % {
                "oois": oois,
                "date": date,
            }
            messages.add_message(self.request, messages.ERROR, error_message)

        return aggregate_report, post_processed_data, report_data

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["report_types"] = [report.class_attributes() for report in self.report_types]
        aggregate_report, post_processed_data, report_data = self.generate_reports_for_oois()
        context["template"] = aggregate_report.template_path
        context["post_processed_data"] = post_processed_data
        context["report_data"] = report_data
        context["report_download_pdf_url"] = url_with_querystring(
            reverse("aggregate_report_pdf", kwargs={"organization_code": self.organization.code}),
            True,
            **self.request.GET,
        )
        context["report_download_json_url"] = url_with_querystring(
            reverse("aggregate_report_view", kwargs={"organization_code": self.organization.code}),
            True,
            **dict(json="true", **self.request.GET),
        )

        context["oois"] = self.get_oois()
        context["plugins"] = self.get_required_optional_plugins(get_plugins_for_report_ids(self.selected_report_types))
        return context


class AggregateReportPDFView(AggregateReportView, WeasyTemplateResponseMixin):
    template_name = "aggregate_report_pdf.html"

    pdf_filename = "aggregate_report.pdf"
    pdf_attachment = False
    pdf_options = {
        "pdf_variant": "pdf/ua-1",
    }
