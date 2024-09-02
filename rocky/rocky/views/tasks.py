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
        try:
            if self.action == self.RESCHEDULE_TASK:
                task_id = self.request.POST.get("task_id", "")
                self.reschedule_task(task_id)
        except HTTPError as exc:
            message = f"HTTP error for {exc.request.url} - {exc}"
            messages.error(request, message)
        except SchedulerError as error:
            messages.error(request, error.message)
        return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["task_filter_form"] = self.get_task_filter_form()
        context["active_filters_counter"] = self.count_active_task_filters()
        context["stats"] = self.get_task_statistics()
        context["breadcrumbs"] = [
            {
                "url": reverse("task_list", kwargs={"organization_code": self.organization.code}),
                "text": _("Tasks"),
            },
        ]
        return context


class BoefjesTaskListView(TaskListView):
    template_name = "tasks/boefjes.html"
    task_type = "boefje"


class NormalizersTaskListView(TaskListView):
    template_name = "tasks/normalizers.html"
    task_type = "normalizer"


class AllTaskListView(SchedulerListView, PageActionsView):
    paginator_class = RockyPaginator
    paginate_by = 20
    context_object_name = "task_list"
    client = scheduler_client(None)
    task_filter_form = TaskFilterForm

    def get_queryset(self):
        task_type = self.request.GET.get("type", self.task_type)
        self.schedulers = [f"{task_type}-{o.code}" for o in self.request.user.organizations]
        form_data = self.task_filter_form(self.request.GET).data.dict()
        kwargs = {k: v for k, v in form_data.items() if v}

        try:
            return LazyTaskList(
                self.client,
                task_type=task_type,
                filters={"filters": [{"column": "scheduler_id", "operator": "in", "value": self.schedulers}]},
                **kwargs,
            )

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
        context["stats"] = self.client.get_combined_schedulers_stats(scheduler_ids=self.schedulers)
        context["breadcrumbs"] = [
            {"url": reverse("all_task_list", kwargs={}), "text": _("All Tasks")},
        ]
        return context


class AllBoefjesTaskListView(AllTaskListView):
    template_name = "tasks/boefjes.html"
    task_type = "boefje"


class AllNormalizersTaskListView(AllTaskListView):
    template_name = "tasks/normalizers.html"
    task_type = "normalizer"
