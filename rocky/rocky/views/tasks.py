from enum import Enum

from django.http import FileResponse, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic.list import ListView
from katalogus.views.mixins import BoefjeMixin, NormalizerMixin

from rocky.paginator import RockyPaginator
from rocky.scheduler import SchedulerError
from rocky.views.scheduler import SchedulerView


class PageActions(Enum):
    RESCHEDULE_TASK = "reschedule_task"


class DownloadTaskDetail(SchedulerView):
    def get(self, request, *args, **kwargs):
        task_id = kwargs["task_id"]
        filename = "task_" + task_id + ".json"
        task_details = self.get_task_details(task_id)
        if task_details is not None:
            response = HttpResponse(FileResponse(task_details.json()), content_type="application/json")
            response["Content-Disposition"] = "attachment; filename=" + filename
            return response

        return redirect(reverse("task_list", kwargs={"organization_code": self.organization.code}))


class TaskListView(SchedulerView, ListView):
    paginate_by = 20
    paginator_class = RockyPaginator

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
        try:
            context["stats"] = self.scheduler_client.get_task_stats(self.task_type, self.task_type)
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


class NormalizersTaskListView(NormalizerMixin, TaskListView):
    template_name = "tasks/normalizers.html"
    task_type = "normalizer"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
