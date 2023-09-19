from account.mixins import OrganizationView
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, TemplateView
from tools.view_helpers import BreadcrumbsMixin

from reports.forms import OOITypeMultiCheckboxForReportForm
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


class ReportView(ReportBreadcrumbs, BaseOOIListView, OrganizationView):
    """One Report Type for one OOI"""

    template_name = "report_view.html"

    def get_success_url(self):
        return redirect(reverse("report_ooi_selection", kwargs={"organization_code": self.organization.code}))

    def post(self, request, *args, **kwargs):
        self.get_queryset()
        return self.get_success_url()
