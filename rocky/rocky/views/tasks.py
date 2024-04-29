from typing import Any

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic.list import ListView
from httpx import HTTPError

from rocky.paginator import RockyPaginator
from rocky.scheduler import SchedulerError, SchedulerValidationError
from rocky.views.page_actions import PageActionsView
from rocky.views.scheduler import SchedulerView


class TaskListView(SchedulerView, ListView, PageActionsView):
    paginator_class = RockyPaginator
    paginate_by = 20

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        try:
            return super().get(request, *args, **kwargs)
        except (SchedulerValidationError, SchedulerError) as error:
            messages.error(self.request, error.message)
            return redirect("health_beautified", organization_code=self.organization.code)

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
        context["breadcrumbs"] = [
            {
                "url": reverse("task_list", kwargs={"organization_code": self.organization.code}),
                "text": _("Tasks"),
            },
        ]
        return context


class BoefjesTaskListView(TaskListView):
    template_name = "tasks/boefjes.html"


class NormalizersTaskListView(TaskListView):
    template_name = "tasks/normalizers.html"
    task_type = "normalizer"
