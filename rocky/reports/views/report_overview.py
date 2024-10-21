from datetime import datetime
from typing import Any

import structlog
from django.contrib import messages
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView

from octopoes.models import Reference
from octopoes.models.exception import ObjectNotFoundException
from octopoes.models.ooi.reports import Report, ReportRecipe
from reports.views.base import ReportBreadcrumbs, get_selection
from rocky.paginator import RockyPaginator
from rocky.views.mixins import OctopoesView, ReportList
from rocky.views.scheduler import SchedulerView

logger = structlog.get_logger(__name__)


class BreadcrumbsReportOverviewView(ReportBreadcrumbs):
    def build_breadcrumbs(self):
        breadcrumbs = super().build_breadcrumbs()
        kwargs = self.get_kwargs()
        selection = get_selection(self.request)
        breadcrumbs += [{"url": reverse("subreports", kwargs=kwargs) + selection, "text": _("Subreports")}]
        return breadcrumbs


class ScheduledReportsView(BreadcrumbsReportOverviewView, SchedulerView, ListView):
    """
    Shows all the reports that have ever been generated for the organization.
    """

    paginate_by = 20
    context_object_name = "reports"
    paginator = RockyPaginator
    template_name = "report_overview/scheduled_reports.html"
    task_type = "report"
    context_object_name = "scheduled_reports"

    def get_recipe_ooi_tree(self, ooi_pk: str) -> ReportRecipe | None:
        try:
            return self.octopoes_api_connector.get_tree(
                Reference.from_str(f"ReportRecipe|{ooi_pk}"),
                valid_time=self.observed_at,
                depth=1,
                types={ReportRecipe, Report},
            )
        except ObjectNotFoundException:
            return messages.error(self.request, f"Report recipe with id {ooi_pk} not found.")

    def get_queryset(self) -> list[dict[str, Any]]:
        report_schedules = self.get_report_schedules()

        recipes = []
        if report_schedules:
            for schedule in report_schedules:
                recipe_id = schedule["data"]["report_recipe_id"]
                # TODO: This is a workaround to get the recipes and reports.
                #  We should create an endpoint for this in octopoes
                recipe_ooi_tree = self.get_recipe_ooi_tree(recipe_id)
                if recipe_ooi_tree is not None:
                    recipe_tree = recipe_ooi_tree.store.values()
                    recipe_ooi = [ooi for ooi in recipe_tree if isinstance(ooi, ReportRecipe)][0]
                    report_oois = [ooi for ooi in recipe_tree if isinstance(ooi, Report)]
                    recipes.append(
                        {
                            "recipe": recipe_ooi,
                            "cron": schedule["schedule"],
                            "deadline_at": datetime.fromisoformat(schedule["deadline_at"]),
                            "reports": report_oois,
                        }
                    )

        return recipes

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["total_oois"] = len(self.object_list)
        return context


class ReportHistoryView(BreadcrumbsReportOverviewView, OctopoesView, ListView):
    """
    Shows all the reports that have ever been generated for the organization.
    """

    paginate_by = 30
    context_object_name = "reports"
    paginator = RockyPaginator
    template_name = "report_overview/report_history.html"

    def get_queryset(self) -> ReportList:
        return ReportList(self.octopoes_api_connector, valid_time=self.observed_at)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["total_oois"] = len(self.object_list)
        return context


class SubreportView(BreadcrumbsReportOverviewView, OctopoesView, ListView):
    """
    Shows all the subreports that belong to the selected parent report.
    """

    paginate_by = 150
    breadcrumbs_step = 2
    context_object_name = "subreports"
    paginator = RockyPaginator
    template_name = "report_overview/subreports.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.report_id = self.request.GET.get("report_id")

    def get_queryset(self) -> ReportList:
        return ReportList(self.octopoes_api_connector, valid_time=self.observed_at, parent_report_id=self.report_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["total_oois"] = len(self.object_list)
        context["parent_report_id"] = self.report_id
        return context
