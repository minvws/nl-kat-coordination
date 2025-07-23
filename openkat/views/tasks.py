from typing import Any

from django.contrib import messages
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic.list import ListView

from openkat.forms.scheduler import TaskFilterForm
from openkat.paginator import OpenKATPaginator
from openkat.scheduler import SchedulerError, scheduler_client
from openkat.views.page_actions import PageActionsView
from openkat.views.scheduler import SchedulerView
from tasks.models import Task


class SchedulerListView(ListView):
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        try:
            return super().get_context_data(**kwargs)
        except SchedulerError as error:
            messages.error(self.request, error.message)
        return {}


class TaskListView(SchedulerView, SchedulerListView, PageActionsView):
    paginator_class = OpenKATPaginator
    paginate_by = 150
    context_object_name = "task_list"

    def get_queryset(self):
        tasks = Task.objects.filter(type=self.task_type).order_by("-created_at")
        form_data = self.get_task_filter_form().data.dict()

        if min_created_at := form_data.get("min_created_at"):
            tasks = tasks.filter(created_at__gte=min_created_at)

        if max_created_at := form_data.get("max_created_at"):
            tasks = tasks.filter(created_at__lte=max_created_at)

        if status := form_data.get("status"):
            tasks = tasks.filter(status=status)

        if input_ooi := form_data.get("input_ooi"):
            tasks = tasks.filter(data__input_ooi=input_ooi)

        if self.organization:
            tasks = tasks.filter(organization=self.organization)

        return tasks

    def post(self, request, *args, **kwargs):
        if self.action == self.RESCHEDULE_TASK:
            task_id = self.request.POST.get("task_id", "")
            self.reschedule_task(task_id)

        return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["task_filter_form"] = self.get_task_filter_form()
        context["active_filters_counter"] = self.count_active_task_filters()
        context["breadcrumbs"] = [
            {"url": reverse("task_list", kwargs={"organization_code": self.organization.code}), "text": _("Tasks")}
        ]
        return context


class BoefjesTaskListView(TaskListView):
    template_name = "tasks/boefjes.html"
    task_type = "boefje"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stats"] = self.get_task_statistics()
        context["breadcrumbs"] = [
            {"url": reverse("task_list", kwargs={"organization_code": self.organization.code}), "text": _("Tasks")},
            {
                "url": reverse("boefjes_task_list", kwargs={"organization_code": self.organization.code}),
                "text": _("Boefjes"),
            },
        ]
        return context


class NormalizersTaskListView(TaskListView):
    template_name = "tasks/normalizers.html"
    task_type = "normalizer"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stats"] = self.get_task_statistics()
        context["breadcrumbs"] = [
            {"url": reverse("task_list", kwargs={"organization_code": self.organization.code}), "text": _("Tasks")},
            {
                "url": reverse("normalizers_task_list", kwargs={"organization_code": self.organization.code}),
                "text": _("Normalizers"),
            },
        ]

        # Search for the corresponding Normalizer names and add those to the task_list
        task_list = context.get("task_list", [])
        ids = {
            task.data["raw_data"]["boefje_meta"]["boefje"]["plugin_id"]
            for task in task_list
            if task.data["raw_data"]["boefje_meta"]["boefje"]["plugin_id"] != "manual"
        }
        plugins = self.get_katalogus().get_plugins(ids=list(ids))
        plugin_dict = {p.plugin_id: p.name for p in plugins}

        for task in task_list:
            boefje_id = task.data["raw_data"]["boefje_meta"]["boefje"]["plugin_id"]
            task.data["raw_data"]["boefje_meta"]["boefje"]["name"] = (
                plugin_dict[boefje_id] if boefje_id != "manual" else "Manual"
            )

        return context


class ReportsTaskListView(TaskListView):
    template_name = "tasks/reports.html"
    task_type = "report"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stats"] = self.get_task_statistics()
        context["breadcrumbs"] = [
            {"url": reverse("task_list", kwargs={"organization_code": self.organization.code}), "text": _("Tasks")},
            {
                "url": reverse("reports_task_list", kwargs={"organization_code": self.organization.code}),
                "text": _("Reports"),
            },
        ]
        return context


class AllTaskListView(SchedulerListView, PageActionsView):
    paginator_class = OpenKATPaginator
    paginate_by = 150
    context_object_name = "task_list"
    client = scheduler_client(None)
    task_filter_form = TaskFilterForm
    task_type: str

    def get_user_organizations(self) -> list[str]:
        return [org.code for org in self.request.user.organizations]

    def get_organization_filter(self) -> dict[str, dict[str, list[dict[str, str | list[str]]]]]:
        if self.request.user.can_access_all_organizations:
            # We don't need to add a filter if the user can access all organizations
            return {}

        return {
            "filters": {
                "filters": [{"column": "organisation", "operator": "in", "value": self.get_user_organizations()}]
            }
        }

    def get_queryset(self):
        form_data = self.task_filter_form(self.request.GET).data.dict()
        tasks = Task.objects.filter(type=self.task_type).order_by("-created_at")

        if "min_created_at" in form_data:
            tasks.filter(created_at__gte=form_data["min_created_at"])

        if "max_created_at" in form_data:
            tasks.filter(created_at__lte=form_data["max_created_at"])

        if "status" in form_data:
            tasks.filter(status=form_data["status"])

        if self.request.user.can_access_all_organizations:
            return tasks

        return tasks.filter(organization__in=self.get_user_organizations())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["task_filter_form"] = self.task_filter_form(self.request.GET)
        if self.request.user.can_access_all_organizations:
            context["stats"] = self.client.get_task_stats_for_all_organizations(self.task_type)
        else:
            context["stats"] = self.client.get_combined_schedulers_stats(self.task_type, self.get_user_organizations())
        context["breadcrumbs"] = [{"url": reverse("all_task_list", kwargs={}), "text": _("All Tasks")}]
        return context


class AllBoefjesTaskListView(AllTaskListView):
    template_name = "tasks/boefjes.html"
    task_type = "boefje"


class AllNormalizersTaskListView(AllTaskListView):
    template_name = "tasks/normalizers.html"
    task_type = "normalizer"


class AllReportsTaskListView(AllTaskListView):
    template_name = "tasks/reports.html"
    task_type = "report"
