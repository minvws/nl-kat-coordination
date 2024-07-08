from collections.abc import Sequence
from typing import Any

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import urlencode
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView

from octopoes.models import ScanProfileType
from octopoes.models.ooi.reports import Report as ReportOOI
from reports.report_types.aggregate_organisation_report.report import AggregateOrganisationReport, aggregate_reports
from reports.report_types.definitions import Report
from reports.report_types.helpers import get_ooi_types_from_aggregate_report, get_report_types_from_aggregate_report
from reports.views.base import (
    REPORTS_PRE_SELECTION,
    ReportBreadcrumbs,
    ReportOOIView,
    ReportPluginView,
    ReportTypeView,
    get_selection,
)
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
                "text": _("Select Objects"),
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
    AggregateReportStepsMixin,
    BreadcrumbsAggregateReportView,
    ReportOOIView,
    BaseOOIListView,
):
    """
    Select Objects for the 'Aggregate Report' flow.
    """

    template_name = "aggregate_report/select_oois.html"
    breadcrumbs_step = 3
    current_step = 1
    ooi_types = get_ooi_types_from_aggregate_report(AggregateOrganisationReport)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_ooi_filter_forms(self.ooi_types))
        context["channel"] = "aggregate_report"
        return context


class ReportTypesSelectionAggregateReportView(
    AggregateReportStepsMixin,
    BreadcrumbsAggregateReportView,
    ReportOOIView,
    ReportTypeView,
    TemplateView,
):
    """
    Shows all possible report types from a list of Objects.
    Chooses report types for the 'Aggregate Report' flow.
    """

    template_name = "aggregate_report/select_report_types.html"
    breadcrumbs_step = 4
    current_step = 2
    ooi_types = get_ooi_types_from_aggregate_report(AggregateOrganisationReport)

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.available_report_types = self.get_report_types_for_aggregate_report(
            get_report_types_from_aggregate_report(AggregateOrganisationReport)
        )

    def get(self, request, *args, **kwargs):
        if not self.selected_oois:
            messages.error(self.request, _("Select at least one OOI to proceed."))
        return super().get(request, *args, **kwargs)

    def get_report_types_for_aggregate_report(
        self, reports_dict: dict[str, set[type[Report]]]
    ) -> dict[str, list[dict[str, str]]]:
        report_types = {}
        for option, reports in reports_dict.items():
            report_types[option] = self.get_report_types(reports)
        return report_types

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["available_report_types_aggregate"] = self.available_report_types
        context["count_available_report_types_aggregate"] = len(self.available_report_types["required"]) + len(
            self.available_report_types["optional"]
        )
        context["total_oois"] = self.get_total_objects()
        return context


class SaveAggregateReportMixin(ReportPluginView):
    def save_report(self) -> ReportOOI:
        input_oois = self.get_oois()

        aggregate_report, post_processed_data, report_data, report_errors = aggregate_reports(
            self.octopoes_api_connector,
            input_oois,
            self.selected_report_types,
            self.observed_at,
            self.organization.code,
        )

        # If OOI could not be found or the date is incorrect, it will be shown to the user as a message error
        if report_errors:
            report_types = ", ".join(set(report_errors))
            date = self.observed_at.date()
            error_message = _("No data could be found for %(report_types). Object(s) did not exist on %(date)s.") % {
                "report_types": report_types,
                "date": date,
            }
            messages.add_message(self.request, messages.ERROR, error_message)

        observed_at = self.get_observed_at()

        post_processed_data["plugins"] = self.get_plugin_data_for_saving()
        post_processed_data["oois"] = []
        for input_ooi in input_oois:
            post_processed_data["oois"].append(
                {
                    "name": input_ooi.human_readable,
                    "type": input_ooi.object_type,
                    "scan_profile_level": input_ooi.scan_profile.level.value if input_ooi.scan_profile else 0,
                    "scan_profile_type": (
                        input_ooi.scan_profile.scan_profile_type if input_ooi.scan_profile else ScanProfileType.EMPTY
                    ),
                }
            )

        post_processed_data["report_types"] = []
        for report_type in self.report_types:
            post_processed_data["report_types"].append(
                {
                    "name": str(report_type.name),
                    "description": str(report_type.description),
                    "label_style": report_type.label_style,
                }
            )

        # Create the report
        report_data_raw_id = self.save_report_raw(data=post_processed_data)
        report_ooi = self.save_report_ooi(
            report_data_raw_id=report_data_raw_id,
            report_type=type(aggregate_report),
            input_oois=[ooi.primary_key for ooi in input_oois],
            parent=None,
            has_parent=False,
            observed_at=observed_at,
        )

        # Save the child reports to bytes
        for ooi, types in report_data.items():
            for report_type, data in types.items():
                self.save_report_raw(data=data)

        return report_ooi


class SetupScanAggregateReportView(
    SaveAggregateReportMixin, AggregateReportStepsMixin, BreadcrumbsAggregateReportView, ReportPluginView
):
    """
    Show required and optional plugins to start scans to generate OOIs to include in report.
    """

    template_name = "aggregate_report/setup_scan.html"
    breadcrumbs_step = 5
    current_step = 3

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if not self.selected_report_types:
            messages.error(self.request, _("Select at least one report type to proceed."))
            return redirect(
                reverse("aggregate_report_select_report_types", kwargs=self.get_kwargs()) + get_selection(self.request)
            )
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


class SaveAggregateReportView(SaveAggregateReportMixin, BreadcrumbsAggregateReportView, ReportPluginView):
    """
    Save the report and redirect to the saved report
    """

    current_step = 6
    ooi_types = get_ooi_types_from_aggregate_report(AggregateOrganisationReport)
    report_types: Sequence[type[Report]]

    def post(self, request, *args, **kwargs):
        report_ooi = self.save_report()

        return redirect(
            reverse("view_report", kwargs={"organization_code": self.organization.code})
            + "?"
            + urlencode({"report_id": report_ooi.reference})
        )
