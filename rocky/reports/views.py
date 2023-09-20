from account.mixins import OrganizationView
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, TemplateView
from tools.view_helpers import BreadcrumbsMixin

from reports.forms import OOITypeMultiCheckboxForReportForm
from reports.report_types.definitions import get_ooi_types_with_report
from rocky.views.ooi_view import BaseOOIListView


class ReportBreadcrumbs(BreadcrumbsMixin):
    def build_breadcrumbs(self):
        breadcrumbs = [
            {
                "url": reverse("report_type_selection", kwargs={"organization_code": self.organization.code}),
                "text": _("Reports"),
            }
        ]

        return breadcrumbs


class ReportTypeSelectionView(ReportBreadcrumbs, OrganizationView, TemplateView):
    template_name = "report_type_selection.html"


class ReportOOISelectionView(ReportBreadcrumbs, BaseOOIListView, OrganizationView, ListView):
    template_name = "report_ooi_selection.html"
    ooi_types = get_ooi_types_with_report()

    def build_breadcrumbs(self):
        breadcrumbs = super().build_breadcrumbs()
        breadcrumbs.append(
            {
                "url": reverse("report_ooi_selection", kwargs={"organization_code": self.organization.code}),
                "text": _("OOI Selection"),
            },
        )
        return breadcrumbs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object_type_filters"] = OOITypeMultiCheckboxForReportForm(self.request.GET)
        return context


class ReportView(ReportBreadcrumbs, OrganizationView):
    """One Report Type for one OOI"""

    template_name = "report_view.html"

    def error_url(self):
        return redirect(reverse("report_ooi_selection", kwargs={"organization_code": self.organization.code}))

    def post(self, request, *args, **kwargs):
        ooi_selection = request.POST.getlist("ooi", [])
        if not ooi_selection:
            messages.add_message(self.request, messages.ERROR, _("Select at least one OOI to proceed."))
            return self.error_url()
        if len(ooi_selection) > 1:
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
        messages.add_message(self.request, messages.SUCCESS, _("Your report is being processed."))
        return redirect(reverse("report_ooi_selection", kwargs={"organization_code": self.organization.code}))
