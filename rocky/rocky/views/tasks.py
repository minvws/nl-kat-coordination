from datetime import datetime
from enum import Enum
from typing import Optional

from account.mixins import OrganizationView
from django.contrib import messages
from django.http import FileResponse, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic.list import ListView
from katalogus.views.mixins import BoefjeMixin, NormalizerMixin

from rocky.scheduler import SchedulerError, TaskNotFoundError, get_scheduler
from rocky.views.scheduler import get_details_of_task, get_list_of_tasks, reschedule_task

TASK_LIMIT = 50


def get_date_time(date: Optional[str] = None) -> Optional[datetime]:
    if date:
        return datetime.strptime(date, "%Y-%m-%d")


class PageActions(Enum):
    RESCHEDULE_TASK = "reschedule_task"


class DownloadTaskDetail(OrganizationView):
    def get(self, request, *args, **kwargs):
        try:
            task_id = kwargs["task_id"]
            filename = "task_" + task_id + ".json"
            task_details = get_details_of_task(request, self.organization.code, task_id)
            response = HttpResponse(FileResponse(task_details.json()), content_type="application/json")
            response["Content-Disposition"] = "attachment; filename=" + filename
            return response
        except TaskNotFoundError as error:
            messages.error(self.request, error.message)
        return redirect(reverse("task_list", kwargs={"organization_code": self.organization.code}))


class TaskListView(OrganizationView, ListView):
    paginate_by = 20
    object_list = []

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)

        self.scheduler_id = self.plugin_type + "-" + self.organization.code
        self.task_type = self.request.GET.get("type", self.plugin_type)
        self.status = self.request.GET.get("scan_history_status", None)
        self.input_ooi = self.request.GET.get("scan_history_search", None)
        self.min_created_at = get_date_time(self.request.GET.get("scan_history_from", None))
        self.max_created_at = get_date_time(self.request.GET.get("scan_history_to", None))

    def get_queryset(self):
        return get_list_of_tasks(
            self.request,
            self.organization.code,
            scheduler_id=self.scheduler_id,
            task_type=self.task_type,
            status=self.status,
            min_created_at=self.min_created_at,
            max_created_at=self.max_created_at,
            input_ooi=self.input_ooi,
        )

    def post(self, request, *args, **kwargs):
        self.handle_page_action(request.POST["action"])
        return redirect(request.path)

    def handle_page_action(self, action: str) -> None:
        if action == PageActions.RESCHEDULE_TASK.value:
            task_id = self.request.POST.get("task_id")
            reschedule_task(self.request, self.organization.code, task_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            scheduler_client = get_scheduler(self.organization.code)
            context["stats"] = scheduler_client.get_task_stats(self.plugin_type)
        except SchedulerError:
            context["stats"] = None
        context["breadcrumbs"] = [
            {"url": reverse("task_list", kwargs={"organization_code": self.organization.code}), "text": _("Tasks")},
        ]

        return context


class BoefjesTaskListView(BoefjeMixin, TaskListView):
    template_name = "tasks/boefjes.html"
    plugin_type = "boefje"


class NormalizersTaskListView(NormalizerMixin, TaskListView):
    template_name = "tasks/normalizers.html"
    plugin_type = "normalizer"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["breadcrumbs"] = [
            {
                "url": reverse("task_list", kwargs={"organization_code": self.organization.code}),
                "text": _("Tasks"),
            },
        ]

        return context
