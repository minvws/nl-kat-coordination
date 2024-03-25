from enum import Enum
from typing import Any

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic.list import ListView

from rocky.paginator import RockyPaginator
from rocky.scheduler import SchedulerError
from rocky.views.scheduler import SchedulerView


class PageActions(Enum):
    RESCHEDULE_TASK = "reschedule_task"


class TaskListView(SchedulerView, ListView):
    paginator_class = RockyPaginator
    paginate_by = 20

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        try:
            super().get(request, *args, **kwargs)
        except SchedulerError as error:
            messages.error(self.request, error.message)
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return self.get_task_list()

    def post(self, request, *args, **kwargs):
        self.handle_page_action(request.POST.get("action", ""))
        return self.get(request, *args, **kwargs)

    def handle_page_action(self, action: str) -> None:
        if action == PageActions.RESCHEDULE_TASK.value:
            task_id = self.request.POST.get("task_id", "")
            self.reschedule_task(task_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {"url": reverse("task_list", kwargs={"organization_code": self.organization.code}), "text": _("Tasks")},
        ]
        try:
            context["stats"] = self.scheduler_client.get_task_stats(self.task_type, self.task_type)
        except SchedulerError:
            context["stats_error"] = True
        else:
            context["stats_error"] = False
        return context


class BoefjesTaskListView(TaskListView):
    template_name = "tasks/boefjes.html"


class NormalizersTaskListView(TaskListView):
    template_name = "tasks/normalizers.html"
    task_type = "normalizer"
