from datetime import datetime
from enum import Enum

from account.mixins import OrganizationView
from django.contrib import messages
from django.http import FileResponse, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from katalogus.views.mixins import BoefjeMixin, NormalizerMixin
from requests import HTTPError
from tools.view_helpers import reschedule_task

from rocky.scheduler import SchedulerError, SchedulerPagintor, TaskNotFoundError, client


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


class TaskListView(OrganizationView, TemplateView):
    plugin_type: str
    paginate_by: int = 10

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.scheduler_id = self.plugin_type + "-" + self.organization.code

    def get_filters(self):
        if self.request.GET.get("scan_history_from"):
            min_created_at = datetime.strptime(self.request.GET.get("scan_history_from"), "%Y-%m-%d")
        else:
            min_created_at = None

        if self.request.GET.get("scan_history_to"):
            max_created_at = datetime.strptime(self.request.GET.get("scan_history_to"), "%Y-%m-%d")
        else:
            max_created_at = None
        return {
            "task_type": self.request.GET.get("type", self.plugin_type),
            "status": self.request.GET.get("scan_history_status", None),
            "input_ooi": self.request.GET.get("scan_history_search", None),
            "min_created_at": min_created_at,
            "max_created_at": max_created_at,
        }

    def get_queryset(self):
        try:
            paginator = SchedulerPagintor(self.scheduler_id, self.paginate_by)
            page_kwarg = "page"
            page = self.kwargs.get(page_kwarg) or self.request.GET.get(page_kwarg) or 1
            return paginator.get_page_objects(int(page), **self.get_filters()).results
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
        context["object_list"] = self.get_queryset()
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
