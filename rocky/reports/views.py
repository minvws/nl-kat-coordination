from account.mixins import OrganizationView
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, TemplateView

from rocky.views.ooi_view import BaseOOIListView


class ReportsBreadcrumbsMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {
                "url": reverse("reports", kwargs={"organization_code": self.organization.code}),
                "text": _("Reports"),
            },
        ]
        return context


class ReportsView(BaseOOIListView, OrganizationView, ReportsBreadcrumbsMixin, ListView):
    template_name = "reports.html"


class GenerateReportView(OrganizationView, ReportsBreadcrumbsMixin, TemplateView):
    template_name = "generate_report.html"
