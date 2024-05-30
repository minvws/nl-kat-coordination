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
                "text": _("Reports history"),
            },
            {
                "url": reverse("subreports", kwargs=kwargs) + selection,
                "text": _("Subreports"),
            },
        ]
        return breadcrumbs


class ReportHistoryView(BreadcrumbsReportOverviewView, OctopoesView, ListView):
    """
    Shows all the reports that have ever been generated for the organization.
    """

    paginate_by = 10
    breadcrumbs_step = 2
    context_object_name = "reports"
    paginator = RockyPaginator
    template_name = "report_overview/report_overview.html"

    def get_queryset(self) -> ReportList:
        return ReportList(
            self.octopoes_api_connector,
            valid_time=self.observed_at,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["total_oois"] = len(self.object_list)
        return context


class SubreportView(BreadcrumbsReportOverviewView, OctopoesView, ListView):
    """
    Shows all the subreports that belong to the selected parent report.
    """

    paginate_by = 20
    breadcrumbs_step = 3
    context_object_name = "subreports"
    paginator = RockyPaginator
    template_name = "report_overview/subreports.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.report_id = self.request.GET.get("report_id", None)

    def get_queryset(self) -> ReportList:
        return ReportList(
            self.octopoes_api_connector,
            valid_time=self.observed_at,
            parent_report_id=self.report_id,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["total_oois"] = len(self.object_list)
        context["parent_report_id"] = self.report_id
        return context


class ReportHistoryPDFView(ReportHistoryView, WeasyTemplateResponseMixin):
    template_name = "report_history_pdf.html"

    pdf_filename = "report_history.pdf"
    pdf_attachment = False
    pdf_options = {
        "pdf_variant": "pdf/ua-1",
    }
