from datetime import datetime
from enum import Enum

from account.mixins import OrganizationView
from django.contrib import messages
from django.http import FileResponse, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic.list import ListView
from httpx import HTTPError
from katalogus.views.mixins import BoefjeMixin, NormalizerMixin
from tools.view_helpers import reschedule_task

from rocky.paginator import RockyPaginator
from rocky.scheduler import SchedulerError, TaskNotFoundError, client


class PageActions(Enum):
    RESCHEDULE_TASK = "reschedule_task"


class DownloadTaskDetail(OrganizationView):
    def get(self, request, *args, **kwargs):
        try:
            task_id = kwargs["task_id"]
            filename = "task_" + task_id + ".json"
            task_details = client.get_task_details(self.organization.code, task_id)
            response = HttpResponse(FileResponse(task_details.json()), content_type="application/json")
            response["Content-Disposition"] = "attachment; filename=" + filename
            return response
        except TaskNotFoundError as error:
            messages.error(self.request, error.message)
        return redirect(reverse("task_list", kwargs={"organization_code": self.organization.code}))


class TaskListView(OrganizationView, ListView):
    paginate_by = 20
    paginator_class = RockyPaginator

    def get_queryset(self):
        scheduler_id = self.plugin_type + "-" + self.organization.code
        task_type = self.request.GET.get("type", self.plugin_type)

        status = self.request.GET.get("scan_history_status") if self.request.GET.get("scan_history_status") else None

        input_ooi = self.request.GET.get("scan_history_search") if self.request.GET.get("scan_history_search") else None

        if self.request.GET.get("scan_history_from"):
            min_created_at = datetime.strptime(self.request.GET.get("scan_history_from"), "%Y-%m-%d")
        else:
            min_created_at = None

        if self.request.GET.get("scan_history_to"):
            max_created_at = datetime.strptime(self.request.GET.get("scan_history_to"), "%Y-%m-%d")
        else:
            max_created_at = None

        try:
            return client.get_lazy_task_list(
                scheduler_id=scheduler_id,
                task_type=task_type,
                status=status,
                min_created_at=min_created_at,
                max_created_at=max_created_at,
                input_ooi=input_ooi,
            )

        except HTTPError:
            error_message = _("Fetching tasks failed: no connection with scheduler")
            messages.add_message(self.request, messages.ERROR, error_message)
            return []

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
            context["stats"] = client.get_task_stats(self.organization.code, self.plugin_type)
        except SchedulerError:
            context["stats_error"] = True
        else:
            context["stats_error"] = False
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
