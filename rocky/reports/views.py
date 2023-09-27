from logging import getLogger
from typing import Any

from account.mixins import OrganizationView
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from tools.view_helpers import BreadcrumbsMixin

from octopoes.models import Reference
from reports.forms import OOITypeMultiCheckboxForReportForm
from reports.report_types.helpers import (
    get_ooi_types_with_report,
    get_plugins_for_report_ids,
    get_report_by_id,
    get_report_types_for_oois,
)
from rocky.views.mixins import OctopoesView
from rocky.views.ooi_view import BaseOOIListView

logger = getLogger(__name__)


class ReportBreadcrumbs(BreadcrumbsMixin):
    current_step: int = 0

    def build_breadcrumbs(self):
        kwargs = {"organization_code": self.organization.code}
        breadcrumbs = [
            {
                "url": reverse("report_oois_selection", kwargs=kwargs),
                "text": _("Reports"),
            },
            {
                "url": reverse("report_type_selection", kwargs=kwargs),
                "text": _("Choose report types"),
            },
            {
                "url": reverse("report_setup_scan", kwargs=kwargs),
                "text": _("Set up scan"),
            },
            {
                "url": reverse("report_view", kwargs=kwargs),
                "text": _("View Report"),
            },
        ]

        return breadcrumbs[: self.current_step]


class ReportOOISelectionView(ReportBreadcrumbs, BaseOOIListView, OrganizationView):
    template_name = "report_oois_selection.html"
    ooi_types = get_ooi_types_with_report()
    current_step = 1

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object_type_filters"] = OOITypeMultiCheckboxForReportForm(self.request.GET)
        return context


class ReportTypeSelectionView(ReportBreadcrumbs, OrganizationView, TemplateView):
    """
    Shows all possible report types from a list of OOIs.
    Chooses report types to generate a report.
    """

    template_name = "report_type_selection.html"
    current_step = 2

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.ooi_selection = request.GET.getlist("ooi", [])
        self.report_types = get_report_types_for_oois(self.ooi_selection)

    def error_url(self):
        return redirect(reverse("report_oois_selection", kwargs={"organization_code": self.organization.code}))

    def get_report_types(self):
        return [
            {"id": report_type.id, "name": report_type.name, "description": report_type.description}
            for report_type in self.report_types
        ]

    def get(self, request, *args, **kwargs):
        if not self.ooi_selection:
            messages.add_message(self.request, messages.ERROR, _("Select at least one OOI to proceed."))
            return self.error_url()
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["oois"] = self.ooi_selection
        context["report_types"] = self.get_report_types()
        return context


class ReportSetupScanView(ReportBreadcrumbs, OrganizationView, TemplateView):
    template_name = "report_setup_scan.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.oois = request.GET.getlist("ooi", [])
        self.report_types = request.GET.getlist("report_type", [])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["plugins"] = get_plugins_for_report_ids(self.report_types)
        return context


class ReportView(ReportBreadcrumbs, OctopoesView, TemplateView):
    template_name = "report.html"
    current_step = 3

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.oois = request.POST.getlist("ooi", [])
        self.report_types = request.POST.getlist("report_type", [])

    def get_reports_data(self):
        report_data = {}
        for ooi in self.oois:
            for report in self.report_types:
                report = get_report_by_id(report)
                if Reference.from_str(ooi).class_type in report.input_ooi_types:
                    data, template = report(self.octopoes_api_connector).generate_data(ooi)
                    report_data[f"{report.name}|{str(ooi)}"] = {"data": data, "template": template}
        return report_data

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["report_data"] = self.get_reports_data()
        return context
