import logging

from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView
from django_weasyprint import WeasyTemplateResponseMixin

from reports.views.base import ReportBreadcrumbs, get_selection
from rocky.paginator import RockyPaginator
from rocky.views.mixins import OctopoesView, ReportList

logger = logging.getLogger(__name__)


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


class ReportHistoryView(BreadcrumbsReportOverviewView, OctopoesView, ListView):
    """
    Shows all the reports that have ever been generated for the organization.
    """

    paginate_by = 100
    context_object_name = "reports"
    paginator = RockyPaginator
    template_name = "report_overview.html"

    def get_queryset(self) -> ReportList:
        return ReportList(
            self.octopoes_api_connector,
            valid_time=self.observed_at,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["total_oois"] = len(self.object_list)
        return context


class ReportHistoryPDFView(ReportHistoryView, WeasyTemplateResponseMixin):
    template_name = "report_history_pdf.html"

    pdf_filename = "report_history.pdf"
    pdf_attachment = False
    pdf_options = {
        "pdf_variant": "pdf/ua-1",
    }
