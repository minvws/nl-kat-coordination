from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from django_weasyprint import WeasyTemplateResponseMixin

from reports.views.base import BaseReportView, ReportBreadcrumbs, get_selection


class BreadcrumbsReportOverviewView(ReportBreadcrumbs):
    def build_breadcrumbs(self):
        breadcrumbs = super().build_breadcrumbs()
        kwargs = self.get_kwargs()
        selection = get_selection(self.request)
        breadcrumbs += [
            {
                "url": reverse("report_history", kwargs=kwargs) + selection,
                "text": _("Report history"),
            },
        ]
        return breadcrumbs


class ReportHistoryView(BreadcrumbsReportOverviewView, BaseReportView, TemplateView):
    """
    Shows all the reports that have ever been generated for the organization.
    """

    template_name = "report_overview.html"

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["oois"] = self.get_oois()
        return context


class ReportHistoryPDFView(ReportHistoryView, WeasyTemplateResponseMixin):
    template_name = "report_history_pdf.html"

    pdf_filename = "report_history.pdf"
    pdf_attachment = False
    pdf_options = {
        "pdf_variant": "pdf/ua-1",
    }
