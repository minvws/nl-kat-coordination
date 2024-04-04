from enum import Enum
from typing import Any

from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic.list import ListView

from rocky.paginator import RockyPaginator
from rocky.views.scheduler import SchedulerView


class PageActions(Enum):
    RESCHEDULE_TASK = "reschedule_task"


class TaskListView(SchedulerView, ListView):
    paginator_class = RockyPaginator
    paginate_by = 20
    object_list: list[Any] = []

    def post(self, request, *args, **kwargs):
        self.handle_page_action(request.POST.get("action", ""))
        return self.get(request, *args, **kwargs)

    def get_queryset(self):
        return self.get_task_list()

    def handle_page_action(self, action: str) -> None:
        if action == PageActions.RESCHEDULE_TASK.value:
            task_id = self.request.POST.get("task_id", "")
            self.reschedule_task(task_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {"url": reverse("task_list", kwargs={"organization_code": self.organization.code}), "text": _("Tasks")},
        ]
        return context


class BoefjesTaskListView(TaskListView):
    template_name = "tasks/boefjes.html"


class NormalizersTaskListView(TaskListView):
    template_name = "tasks/normalizers.html"
    task_type = "normalizer"
