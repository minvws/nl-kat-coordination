from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import structlog
from django.contrib import messages
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView
from pydantic import TypeAdapter
from tools.ooi_helpers import create_ooi

from octopoes.models import OOI, Reference
from octopoes.models.exception import ObjectNotFoundException
from octopoes.models.ooi.reports import Report, ReportRecipe
from reports.report_types.aggregate_organisation_report.report import aggregate_reports
from reports.report_types.helpers import get_report_by_id
from reports.views.base import ReportBreadcrumbs, ReportDataDict, get_selection
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
                if schedule["data"]:
                    recipe_id = schedule["data"]["report_recipe_id"]
                    # TODO: This is a workaround to get the recipes and reports.
                    #  We should create an endpoint for this in octopoes
                    recipe_ooi_tree = self.get_recipe_ooi_tree(recipe_id)
                    if recipe_ooi_tree is not None:
                        recipe_tree = recipe_ooi_tree.store.values()
                        recipe_ooi = next(ooi for ooi in recipe_tree if isinstance(ooi, ReportRecipe))
                        report_oois = [ooi for ooi in recipe_tree if isinstance(ooi, Report)]
                        recipes.append(
                            {
                                "schedule_id": schedule["id"],
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

    def post(self, request, *args, **kwargs):
        self.run_bulk_actions()
        return self.get(request, *args, **kwargs)

    def get_queryset(self) -> ReportList:
        return ReportList(self.octopoes_api_connector, valid_time=self.observed_at)

    def get_report_ooi(self, ooi_pk: str) -> Report:
        return self.octopoes_api_connector.get(Reference.from_str(f"{ooi_pk}"), valid_time=datetime.now(timezone.utc))

    def run_bulk_actions(self) -> None:
        action = self.request.POST.get("action", "")
        report_references = self.request.POST.getlist("report_reference", [])

        if action == "rename":
            return self.rename_reports(report_references)

        if action == "delete":
            return self.delete_reports(report_references)

        if action == "rerun":
            return self.rerun_reports(report_references)

    def delete_reports(self, report_references: list[str]) -> None:
        self.octopoes_api_connector.delete_many(report_references, datetime.now(timezone.utc))
        messages.success(self.request, _("Deletion successful."))

    def rerun_reports(self, report_references: list[str]) -> None:
        for report_id in report_references:
            actual_report_ooi = self.get_report_ooi(report_id)

            # First create new parent report and then create all subreports with new parent reference
            if actual_report_ooi.report_type == "concatenated-report":
                self.rerun_concatenated_report(actual_report_ooi)

            if actual_report_ooi.report_type == "aggregate-organisation-report":
                self.rerun_aggregate_report(actual_report_ooi)

    def get_input_data(self, report_ooi: Report) -> dict[str, Any]:
        self.bytes_client.login()
        report_data = TypeAdapter(Any, config={"arbitrary_types_allowed": True}).validate_json(
            self.bytes_client.get_raw(raw_id=report_ooi.data_raw_id)
        )
        return {
            "input_data": {
                "input_oois": report_data["input_data"]["input_oois"],
                "report_types": report_data["input_data"]["report_types"],
                "plugins": report_data["input_data"]["plugins"],
            }
        }

    def get_input_oois(self, ooi_pks: list[str]) -> list[type[OOI]]:
        return [
            self.octopoes_api_connector.get(Reference.from_str(ooi), valid_time=self.observed_at) for ooi in ooi_pks
        ]

    def recreate_report(
        self, report_ooi: Report, observed_at: datetime, bytes_id: str, parent_report_ooi: Report | None = None
    ) -> Report:
        """Recreate a report with new observed_at and new (bytes) data."""

        new_report_ooi = Report(
            name=report_ooi.name,
            report_type=report_ooi.report_type,
            template=report_ooi.template,
            report_id=uuid4(),
            organization_code=report_ooi.organization_code,
            organization_name=report_ooi.organization_name,
            organization_tags=report_ooi.organization_tags,
            data_raw_id=bytes_id,
            date_generated=observed_at,
            input_oois=report_ooi.input_oois,
            observed_at=observed_at,
            parent_report=report_ooi.parent_report if parent_report_ooi is None else parent_report_ooi.reference,
            report_recipe=report_ooi.report_recipe,
            has_parent=report_ooi.has_parent if parent_report_ooi is None else True,
        )

        create_ooi(self.octopoes_api_connector, self.bytes_client, new_report_ooi, observed_at)

        return new_report_ooi

    def rerun_aggregate_report(self, report_ooi: Report) -> None:
        observed_at = datetime.now(timezone.utc)
        report_input_data = self.get_input_data(report_ooi)
        report_types = report_input_data["input_data"]["report_types"]

        _, post_processed_data, _, _ = aggregate_reports(
            self.octopoes_api_connector,
            self.get_input_oois(report_ooi.input_oois),
            report_types,
            observed_at,
            report_ooi.organization_code,
        )

        bytes_id = self.bytes_client.upload_raw(
            raw=ReportDataDict(post_processed_data | report_input_data).model_dump_json().encode(),
            manual_mime_types={"openkat/report"},
        )

        self.recreate_report(report_ooi, observed_at, bytes_id)

    def rerun_concatenated_report(self, report_ooi: Report) -> None:
        observed_at = datetime.now(timezone.utc)
        report_input_data = self.get_input_data(report_ooi)
        bytes_id = self.bytes_client.upload_raw(
            raw=ReportDataDict(report_input_data).model_dump_json().encode(), manual_mime_types={"openkat/report"}
        )

        parent_ooi = self.recreate_report(report_ooi, observed_at, bytes_id)

        subreports = self.octopoes_api_connector.query(
            "Report.<parent_report[is Report]", valid_time=observed_at, source=report_ooi.reference
        )

        for subreport_ooi in subreports:
            sub_report_type = get_report_by_id(subreport_ooi.report_type)
            sub_report_data = sub_report_type(self.octopoes_api_connector).collect_data(
                subreport_ooi.input_oois, observed_at
            )
            for ooi, data in sub_report_data.items():
                required_plugins = list(report_input_data["input_data"]["plugins"]["required"])
                optional_plugins = list(report_input_data["input_data"]["plugins"]["optional"])

                child_plugins: dict[str, list[str]] = {"required": [], "optional": []}

                child_plugins["required"] = [
                    plugin_id for plugin_id in required_plugins if plugin_id in sub_report_type.plugins["required"]
                ]
                child_plugins["optional"] = [
                    plugin_id for plugin_id in optional_plugins if plugin_id in sub_report_type.plugins["optional"]
                ]

                child_input_data = {
                    "input_data": {
                        "input_oois": [ooi],
                        "report_types": [subreport_ooi.report_type],
                        "plugins": child_plugins,
                    }
                }

                bytes_id_subreport = self.bytes_client.upload_raw(
                    raw=ReportDataDict({"report_data": data} | child_input_data).model_dump_json().encode(),
                    manual_mime_types={"openkat/report"},
                )

                self.recreate_report(subreport_ooi, observed_at, bytes_id_subreport, parent_ooi)

    def rename_reports(self, report_references: list[str]) -> None:
        report_names = self.request.POST.getlist("report_name", [])

        if not report_references or not report_names:
            messages.error(self.request, _("Renaming failed. Empty report name found."))

        if len(report_references) != len(report_names):
            messages.error(self.request, _("Report names and reports does not match."))

        for index, report_id in enumerate(report_references):
            report_ooi = self.get_report_ooi(report_id)
            report_ooi.name = report_names[index]
            create_ooi(self.octopoes_api_connector, self.bytes_client, report_ooi, datetime.now(timezone.utc))
            messages.success(self.request, _("Report names changed successfully."))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["total_oois"] = len(self.object_list)
        context["selected_reports"] = self.request.GET.getlist("report", [])
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
