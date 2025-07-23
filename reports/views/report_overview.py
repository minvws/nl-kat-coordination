from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import structlog
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView
from httpx import HTTPStatusError
from pydantic import ValidationError

from account.mixins import OrganizationPermissionRequiredMixin
from octopoes.models import Reference
from octopoes.models.exception import ObjectNotFoundException
from octopoes.models.ooi.reports import AssetReport, BaseReport, HydratedReport, Report, ReportRecipe
from openkat.ooi_helpers import create_ooi
from openkat.paginator import OpenKATPaginator
from openkat.views.mixins import OctopoesView, ReportList
from openkat.views.scheduler import SchedulerView
from reports.views.base import ReportBreadcrumbs, get_selection
from tasks.models import Schedule

logger = structlog.get_logger(__name__)


class BreadcrumbsReportOverviewView(ReportBreadcrumbs):
    def build_breadcrumbs(self):
        breadcrumbs = super().build_breadcrumbs()
        kwargs = self.get_kwargs()
        selection = get_selection(self.request)
        breadcrumbs += [{"url": reverse("subreports", kwargs=kwargs) + selection, "text": _("Asset reports")}]
        return breadcrumbs


class ScheduledReportsView(BreadcrumbsReportOverviewView, SchedulerView, ListView):
    """
    Shows all the reports that have ever been generated for the organization.
    """

    paginate_by = 20
    context_object_name = "reports"
    paginator = OpenKATPaginator
    template_name = "report_overview/scheduled_reports.html"
    task_type = "report"
    context_object_name = "scheduled_reports"

    def get_recipe_ooi(self, recipe_id: str) -> ReportRecipe | None:
        try:
            return self.octopoes_api_connector.get(
                Reference.from_str(f"ReportRecipe|{recipe_id}"), valid_time=self.observed_at
            )
        except (HTTPStatusError, ObjectNotFoundException):
            return None

    def get_reports(self, recipe_id: str) -> list[HydratedReport]:
        try:
            return self.octopoes_api_connector.list_reports(
                valid_time=self.observed_at, recipe_id=UUID(recipe_id)
            ).items
        except (HTTPStatusError, ObjectNotFoundException):
            return []

    def get_queryset(self) -> list[dict[str, Any]]:
        report_schedules = self.get_report_schedules()
        if not report_schedules:
            return []

        recipes = []
        for schedule in report_schedules:
            if not schedule["data"]:
                continue

            recipe_id = schedule["data"]["report_recipe_id"]
            report_recipe = self.get_recipe_ooi(recipe_id)
            reports = self.get_reports(recipe_id)
            schedule_datetime = schedule["deadline_at"]
            recipes.append(
                {
                    "schedule_id": schedule["id"],
                    "enabled": schedule["enabled"],
                    "recipe": report_recipe,
                    "cron": schedule["schedule"],
                    "deadline_at": schedule_datetime if schedule_datetime else "asap",
                    "reports": reports,
                    "total_oois": len(
                        {asset_report.input_ooi for report in reports for asset_report in report.input_oois}
                    ),
                }
            )

        return recipes

    def post(self, request, *args, **kwargs):
        recipe_pk = request.POST.get("report_recipe", "")
        schedule_id = request.POST.get("schedule_id", "")

        if not self.organization_member.has_perm("openkat.can_delete_oois"):
            messages.error(self.request, _("Not enough permissions"))
            return self.get(request, *args, **kwargs)

        if recipe_pk and schedule_id and Reference.from_str(recipe_pk).class_type == ReportRecipe:
            try:
                Schedule.objects.get(id=schedule_id).delete()
            except Schedule.DoesNotExist:
                messages.error(self.request, _("Schedule not found."))

            try:
                self.octopoes_api_connector.delete(Reference.from_str(recipe_pk), valid_time=datetime.now(timezone.utc))
                logger.info(
                    "Schedule and reportRecipe deleted", event_code="0800083", schedule_id=schedule_id, recipe=recipe_pk
                )
                messages.success(self.request, _("Recipe '{}' deleted successfully").format(recipe_pk))
            except ObjectNotFoundException:
                messages.error(self.request, _("Recipe not found."))

        else:
            messages.error(self.request, _("No schedule or recipe selected"))

        return redirect(reverse("scheduled_reports", kwargs={"organization_code": self.organization.code}))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["total_report_schedules"] = len(self.object_list)
        return context


class ScheduledReportsEnableDisableView(
    OrganizationPermissionRequiredMixin, BreadcrumbsReportOverviewView, SchedulerView, ListView
):
    """
    Enable/disable the schedule for the selected ReportRecipe.
    """

    task_type = "report"
    template_name = "report_overview/scheduled_reports.html"
    permission_required = "openkat.can_enable_disable_schedule"

    def get_queryset(self) -> ReportList:
        return ReportList(self.octopoes_api_connector, valid_time=self.observed_at)

    def post(self, request, *args, **kwargs) -> HttpResponse:
        recipe_id = request.POST.get("recipe_id")
        report_name_format = request.POST.get("report_name_format")

        schedule = Schedule.objects.filter(data__report_recipe_id=recipe_id).first() if recipe_id else None

        if schedule:
            schedule.enabled = not schedule.enabled
            schedule.save()

            if not schedule.enabled:
                messages.success(
                    self.request,
                    _(
                        "Schedule disabled successfully. '{}' will not be generated "
                        "automatically until the schedule is enabled again."
                    ).format(report_name_format),
                )
            else:
                messages.success(
                    self.request,
                    _("Schedule enabled successfully. '{}' will be generated according to schedule.").format(
                        report_name_format
                    ),
                )

        return redirect(reverse("scheduled_reports", kwargs={"organization_code": self.organization.code}))


class ReportHistoryView(BreadcrumbsReportOverviewView, SchedulerView, OctopoesView, ListView):
    """
    Shows all the reports that have ever been generated for the organization.
    """

    paginate_by = 30
    context_object_name = "reports"
    paginator = OpenKATPaginator
    template_name = "report_overview/report_history.html"
    task_type = "report"

    def post(self, request, *args, **kwargs):
        try:
            self.run_bulk_actions()
        except (ObjectNotFoundException, ValidationError):
            messages.error(request, _("An unexpected error occurred, please check logs for more info."))
        return self.get(request, *args, **kwargs)

    def get_queryset(self) -> ReportList:
        return ReportList(self.octopoes_api_connector, valid_time=self.observed_at)

    def get_report_ooi(self, ooi_pk: str) -> HydratedReport:
        return self.octopoes_api_connector.get_report(ooi_pk, valid_time=self.observed_at)

    def run_bulk_actions(self) -> None:
        action = self.request.POST.get("action", "")
        report_references = self.request.POST.getlist("report_reference", [])
        logger.error("Report_references: %s", report_references)

        if action == "rename":
            return self.rename_reports(report_references)

        if action == "delete":
            return self.delete_reports(report_references)

        if action == "rerun":
            return self.rerun_reports(report_references)

    def delete_reports(self, report_references: list[Reference]) -> None:
        if not self.organization_member.has_perm("openkat.can_delete_oois"):
            messages.error(self.request, _("Not enough permissions"))
            return

        for report_reference in report_references:
            if not issubclass(Reference.from_str(report_reference).class_type, BaseReport):
                messages.error(self.request, _("Other OOI type selected than Report"))
                return

        self.octopoes_api_connector.delete_many(report_references, datetime.now(timezone.utc))
        logger.info("Reports deleted", event_code=800073, reports=report_references)
        messages.success(self.request, _("Deletion successful."))

    def rerun_reports(self, report_references: list[str]) -> None:
        for report_id in report_references:
            report_ooi = self.get_report_ooi(report_id)

            if report_ooi.report_type == "multi-organization-report":
                return messages.warning(
                    self.request,
                    _(
                        "Multi organization reports cannot be rescheduled. "
                        "It consists of imported data from different organizations "
                        "and is not based on newly generated data."
                    ),
                )
            else:
                self.rerun_report(report_ooi)

                for asset_report in report_ooi.input_oois:
                    self.rerun_report(asset_report)

        messages.success(
            self.request, _("Rerun successful. It may take a moment before the new report has been generated.")
        )

    def rerun_report(self, report_ooi: Report | AssetReport):
        """Rerun an existing Report and its AssetReports."""
        deadline_at = datetime.now(timezone.utc).isoformat()
        report_recipe_id = str(report_ooi.report_recipe.tokenized.recipe_id)
        Schedule.objects.filter(data__report_recipe_id=report_recipe_id).update(deadline_at=deadline_at)

    def rename_reports(self, report_references: list[str]) -> None:
        report_names = self.request.POST.getlist("report_name", [])
        error_reports = []

        if not report_references or not report_names:
            messages.error(self.request, _("Renaming failed. Empty report name found."))

        if len(report_references) != len(report_names):
            messages.error(self.request, _("Report names and reports does not match."))

        for index, report_id in enumerate(report_references):
            report_ooi = self.get_report_ooi(report_id).to_report()
            report_ooi.name = report_names[index]
            try:
                create_ooi(self.octopoes_api_connector, report_ooi, datetime.now(timezone.utc))
            except ValidationError:
                error_reports.append(f'"{report_ooi.name}"')

        if not error_reports:
            logger.info("Reports created", event_code=800071, reports=report_references)
            return messages.success(self.request, _("Reports successfully renamed."))

        return messages.error(self.request, _("Report {} could not be renamed.").format(", ".join(error_reports)))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["total_reports"] = len(self.object_list)
        context["selected_reports"] = self.request.GET.getlist("report", [])
        return context


class SubreportView(BreadcrumbsReportOverviewView, OctopoesView, ListView):
    """
    Shows all the subreports that belong to the selected parent report.
    """

    paginate_by = 150
    breadcrumbs_step = 2
    context_object_name = "asset_reports"
    paginator = OpenKATPaginator
    template_name = "report_overview/subreports.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.report_id = self.request.GET.get("report_id")

    def get_queryset(self) -> ReportList:
        return ReportList(self.octopoes_api_connector, valid_time=self.observed_at, report_id=self.report_id)

    def get_report_ooi(self, ooi_pk: str) -> HydratedReport:
        return self.octopoes_api_connector.get_report(ooi_pk, valid_time=self.observed_at)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["total_oois"] = len(self.object_list)
        context["report_ooi"] = self.get_report_ooi(self.report_id).to_report()
        return context
