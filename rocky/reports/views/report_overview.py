from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView

from reports.views.base import ReportBreadcrumbs, get_selection
from rocky.paginator import RockyPaginator
from rocky.scheduler import scheduler_client
from rocky.views.mixins import OctopoesView, ReportList


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


class ScheduledReportsView(BreadcrumbsReportOverviewView, OctopoesView, ListView):
    """
    Shows all the reports that have ever been generated for the organization.
    """

    paginate_by = 20
    breadcrumbs_step = 2
    context_object_name = "reports"
    paginator = RockyPaginator
    template_name = "report_overview/scheduled_reports.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.client = scheduler_client(self.organization.code)

    def get_queryset(self):
        scheduler_id = f"report-{self.organization.code}"
        self.scheduled_reports = self.client.get_scheduled_reports(scheduler_id=scheduler_id)
        return self.scheduled_reports

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["scheduled_reports"] = self.scheduled_reports
        return context


class ReportHistoryView(BreadcrumbsReportOverviewView, OctopoesView, ListView):
    """
    Shows all the reports that have ever been generated for the organization.
    """

    paginate_by = 30
    breadcrumbs_step = 2
    context_object_name = "reports"
    paginator = RockyPaginator
    template_name = "report_overview/report_history.html"

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

    paginate_by = 150
    breadcrumbs_step = 3
    context_object_name = "subreports"
    paginator = RockyPaginator
    template_name = "report_overview/subreports.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.report_id = self.request.GET.get("report_id")

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
