from logging import getLogger

from account.mixins import OrganizationView
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from tools.view_helpers import BreadcrumbsMixin

from reports.forms import OOITypeMultiCheckboxForReportForm
from reports.report_types.helpers import get_ooi_types_with_report, get_report_types_for_oois
from rocky.views.mixins import OctopoesView
from rocky.views.ooi_view import BaseOOIListView

logger = getLogger(__name__)


class ReportBreadcrumbs(BreadcrumbsMixin):
    current_step: int = 0

    def build_breadcrumbs(self):
        kwargs = {"organization_code": self.organization.code}
        breadcrumbs = [
            {
                "url": reverse("report_type_selection", kwargs=kwargs),
                "text": _("Reports"),
            },
            {
                "url": reverse("report_oois_selection", kwargs=kwargs),
                "text": _("OOI Selection"),
            },
            {
                "url": reverse("report_selection", kwargs=kwargs),
                "text": _("Select Report"),
            },
        ]

        return breadcrumbs[: self.current_step]


class ReportTypeSelectionView(ReportBreadcrumbs, OrganizationView, TemplateView):
    current_step = 1
    template_name = "report_type_selection.html"


class ReportOOISelectionView(ReportBreadcrumbs, BaseOOIListView, OrganizationView):
    template_name = "report_oois_selection.html"
    ooi_types = get_ooi_types_with_report()
    current_step = 2

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object_type_filters"] = OOITypeMultiCheckboxForReportForm(self.request.GET)
        return context


class ReportSelectionView(ReportBreadcrumbs, OrganizationView, TemplateView):
    """One Report Type for one OOI"""

    template_name = "report_selection.html"
    current_step = 3

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.ooi_selection = request.POST.getlist("ooi", [])

    def error_url(self):
        return redirect(reverse("report_oois_selection", kwargs={"organization_code": self.organization.code}))

    def post(self, request, *args, **kwargs):
        if not self.ooi_selection:
            messages.add_message(self.request, messages.ERROR, _("Select at least one OOI to proceed."))
            return self.error_url()
        if len(self.ooi_selection) > 1:
            messages.add_message(
                self.request,
                messages.WARNING,
                _(
                    "For now we can only generate a report for only one OOI. "
                    "Please select you preferred OOI from the list. "
                    "We are working to make it possible to view a report over more OOIs."
                ),
            )
            return self.error_url()
        logger.error("OOI selection is: %s", str(self.ooi_selection))
        logger.error("Reports are: %s", str(get_report_types_for_oois(self.ooi_selection)))
        messages.add_message(self.request, messages.SUCCESS, _("Your report is being processed."))
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["oois"] = self.ooi_selection
        context["report_types"] = get_report_types_for_oois(self.ooi_selection)
        return context


class ReportView(OctopoesView):
    template_name = "report.html"

    def get_reports_data(self, request, *args, **kwargs):
        report_data = {}
        for ooi in request.POST.getlist("oois", []):
            for report in request.POST.getlist("report_types", []):
                if ooi.get_type() in report.input_ooi_types:
                    data, template = report(self.octopoes_api_connector).generate_report(ooi)
                    report_data[f"{report.name}|{str(ooi.primary_key)}"] = {"data": data, "template": template}
        return report_data

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["report_data"] = self.get_reports_data(self.request, *self.args, **self.kwargs)
        return context
