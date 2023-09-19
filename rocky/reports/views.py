from account.mixins import OrganizationView
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, TemplateView
from tools.forms.ooi_form import ClearanceLevelFilterForm
from tools.view_helpers import BreadcrumbsMixin

from octopoes.models import ScanLevel, ScanProfileType
from reports.forms import OOITypeMultiCheckboxForReportForm
from rocky.views.mixins import OOIList
from rocky.views.ooi_view import BaseOOIListView


class ReportBreadcrumbs(BreadcrumbsMixin):
    def build_breadcrumbs(self):
        breadcrumbs = [
            {
                "url": reverse("reports", kwargs={"organization_code": self.organization.code}),
                "text": _("Reports"),
            }
        ]

        return breadcrumbs


class ReportView(ReportBreadcrumbs, OrganizationView, TemplateView):
    template_name = "choose_report_type.html"


class OOIReportView(ReportBreadcrumbs, BaseOOIListView, OrganizationView, ListView):
    template_name = "choose_oois.html"

    def get_queryset(self) -> OOIList:
        """Show only declared OOIs"""
        selected_clearance_level = self.request.GET.getlist("clearance_level")
        if selected_clearance_level is not None:
            scan_levels = {ScanLevel(int(s)) for s in selected_clearance_level}
        return self.get_list(
            self.get_observed_at(), scan_level=scan_levels, scan_profile_type={ScanProfileType("declared")}
        )

    def build_breadcrumbs(self):
        breadcrumbs = super().build_breadcrumbs()
        breadcrumbs.append(
            {
                "url": reverse("ooi_report", kwargs={"organization_code": self.organization.code}),
                "text": _("OOI Report"),
            },
        )
        return breadcrumbs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object_type_filters"] = OOITypeMultiCheckboxForReportForm(self.request.GET)
        context["clearance_level_filter_form"] = ClearanceLevelFilterForm(self.request.GET)
        return context


class GenerateReportView(ReportBreadcrumbs, OrganizationView, TemplateView):
    """One Report Type for one OOI"""

    pass
