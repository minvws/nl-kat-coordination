from typing import Any

from django.contrib import messages
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic.list import ListView
from httpx import HTTPError
from tools.forms.scheduler import TaskFilterForm

from rocky.paginator import RockyPaginator
from rocky.scheduler import LazyTaskList, SchedulerError, scheduler_client
from rocky.views.page_actions import PageActionsView
from rocky.views.scheduler import SchedulerView


class SchedulerListView(ListView):
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        try:
            return super().get_context_data(**kwargs)
        except SchedulerError as error:
            messages.error(self.request, error.message)
        return {}


class TaskListView(SchedulerView, SchedulerListView, PageActionsView):
    paginator_class = RockyPaginator
    paginate_by = 150
    context_object_name = "task_list"

    def get_queryset(self):
        return self.get_task_list()

    def post(self, request, *args, **kwargs):
        if self.action == self.RESCHEDULE_TASK:
            task_id = self.request.POST.get("task_id", "")
            self.reschedule_task(task_id)

        return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["task_filter_form"] = self.get_task_filter_form()
        context["active_filters_counter"] = self.count_active_task_filters()
        context["stats"] = self.get_task_statistics()
        context["breadcrumbs"] = [
            {"url": reverse("task_list", kwargs={"organization_code": self.organization.code}), "text": _("Tasks")}
        ]
        return context


class BoefjesTaskListView(TaskListView):
    template_name = "tasks/boefjes.html"
    task_type = "boefje"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

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
        context["breadcrumbs"] = [
            {"url": reverse("task_list", kwargs={"organization_code": self.organization.code}), "text": _("Tasks")},
            {
                "url": reverse("normalizers_task_list", kwargs={"organization_code": self.organization.code}),
                "text": _("Normalizers"),
            },
        ]

        # Search for the corresponding Boefje names and add those to the task_list
        task_list = context.get("task_list", [])
        ids = [
            task.data.raw_data.boefje_meta.boefje.id
            for task in task_list
            if task.data.raw_data.boefje_meta.boefje.id != "manual"
        ]
        plugins = self.get_katalogus().get_plugins(ids=ids)
        plugin_dict = {p.id: p.name for p in plugins}

        for task in task_list:
            boefje_id = task.data.raw_data.boefje_meta.boefje.id
            task.data.raw_data.boefje_meta.boefje.name = plugin_dict[boefje_id] if boefje_id != "manual" else "Manual"

        return context


class ReportsTaskListView(TaskListView):
    template_name = "tasks/report_tasks.html"
    paginate_by = 25
    context_object_name = "report_task_list"
    task_type = "report"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["breadcrumbs"] = [
            {"url": reverse("task_list", kwargs={"organization_code": self.organization.code}), "text": _("Tasks")},
            {
                "url": reverse("reports_task_list", kwargs={"organization_code": self.organization.code}),
                "text": _("Reports"),
            },
        ]
        return context


class AllTaskListView(SchedulerListView, PageActionsView):
    paginator_class = RockyPaginator
    paginate_by = 20
    context_object_name = "task_list"
    client = scheduler_client(None)
    task_filter_form = TaskFilterForm

    def get_user_organizations(self) -> list[str]:
        return [org.code for org in self.request.user.organizations]

    def get_all_organizations_tasks(self) -> dict[str, dict[str, list[dict[str, str | list[str]]]]]:
        if not self.request.user.is_anonymous:
            return {
                "filters": {
                    "filters": [{"column": "organisation", "operator": "in", "value": self.get_user_organizations()}]
                }
            }
        return {}

    def get_task_type(self) -> str:
        return self.request.GET.get("type", self.task_type)

    def get_queryset(self):
        form_data = self.task_filter_form(self.request.GET).data.dict()
        kwargs = {k: v for k, v in form_data.items() if v} | self.get_all_organizations_tasks()

        try:
            return LazyTaskList(self.client, task_type=self.get_task_type(), **kwargs)

        except HTTPError as error:
            error_message = _(f"Fetching tasks failed: no connection with scheduler: {error}")
            messages.add_message(self.request, messages.ERROR, error_message)
            return []
        except SchedulerError as error:
            messages.add_message(self.request, messages.ERROR, str(error))
            return []

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["task_filter_form"] = self.task_filter_form(self.request.GET)
        context["stats"] = self.client.get_combined_schedulers_stats(
            self.get_task_type(), self.get_user_organizations()
        )
        context["breadcrumbs"] = [{"url": reverse("all_task_list", kwargs={}), "text": _("All Tasks")}]
        return context


class AllBoefjesTaskListView(AllTaskListView):
    template_name = "tasks/boefjes.html"
    task_type = "boefje"


class AllNormalizersTaskListView(AllTaskListView):
    template_name = "tasks/normalizers.html"
    task_type = "normalizer"
