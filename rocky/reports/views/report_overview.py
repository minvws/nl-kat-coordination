from datetime import datetime, time, timezone

from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django_weasyprint import WeasyTemplateResponseMixin

from octopoes.models.ooi.reports import Report
from reports.views.base import ReportBreadcrumbs, get_selection
from rocky.views.ooi_view import BaseOOIListView


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


class ReportHistoryView(BreadcrumbsReportOverviewView, BaseOOIListView):
    """
    Shows all the reports that have ever been generated for the organization.
    """

    template_name = "report_overview.html"
    ooi_types = {Report}
    context_object_name = "reports"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        # Set time to end of day to fetch today created objects.
        self.observed_at: datetime = datetime.combine(self.observed_at, time.max, tzinfo=timezone.utc)


class ReportHistoryPDFView(ReportHistoryView, WeasyTemplateResponseMixin):
    template_name = "report_history_pdf.html"

    pdf_filename = "report_history.pdf"
    pdf_attachment = False
    pdf_options = {
        "pdf_variant": "pdf/ua-1",
    }
