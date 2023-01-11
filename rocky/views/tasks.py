import json

from django.contrib import messages
from django.http import FileResponse, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import View
from django.views.generic.list import ListView
from django_otp.decorators import otp_required
from requests import HTTPError
from two_factor.views.utils import class_view_decorator

from rocky.scheduler import client
from tools.models import Organization

TASK_LIMIT = 50


@class_view_decorator(otp_required)
class DownloadTaskDetail(View):
    def get(self, request, *args, **kwargs):
        task_id = kwargs["task_id"]
        filename = "task_" + task_id + ".json"
        task_details = client.get_task_details(task_id)
        if not self.is_task_id(task_id) or "detail" in task_details:
            return self.show_error_message()
        response = HttpResponse(FileResponse(json.dumps(task_details)), content_type="application/json")
        response["Content-Disposition"] = "attachment; filename=" + filename
        return response

    def is_task_id(self, task_id):
        forbidden_chars = ["/", ".", " "]
        for char in forbidden_chars:
            return char not in str(task_id)

    def show_error_message(self):
        error_message = _("Task details not found.")
        messages.add_message(self.request, messages.ERROR, error_message)
        return redirect(reverse("task_list"))


@class_view_decorator(otp_required)
class TaskListView(ListView):
    paginate_by = 20

    def setup(self, request, *args, **kwargs):
        self.scheduler_id = None
        self.org: Organization = request.active_organization

        if self.org:
            self.scheduler_id = self.plugin_type + "-" + self.org.code
        else:
            error_message = _("Organization could not be found")
            messages.add_message(request, messages.ERROR, error_message)

        return super().setup(request, *args, **kwargs)

    def get_queryset(self):
        if not self.scheduler_id:
            return []

        scheduler_id = self.request.GET.get("scheduler_id", self.scheduler_id)
        type_ = self.request.GET.get("type", self.plugin_type)
        status = self.request.GET.get("status", None)
        min_created_at = self.request.GET.get("min_created_at", None)
        max_created_at = self.request.GET.get("max_created_at", None)

        try:
            return client.get_lazy_task_list(
                scheduler_id=scheduler_id,
                object_type=type_,
                status=status,
                min_created_at=min_created_at,
                max_created_at=max_created_at,
            )
        except HTTPError:
            error_message = _("Fetching tasks failed: no connection with scheduler")
            messages.add_message(self.request, messages.ERROR, error_message)
            return []

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {"url": reverse("ooi_list"), "text": _("Objects")},
            {"url": reverse("task_list"), "text": _("Tasks")},
        ]
        return context


@class_view_decorator(otp_required)
class BoefjesTaskListView(TaskListView):
    template_name = "tasks/boefjes.html"
    plugin_type = "boefje"


@class_view_decorator(otp_required)
class NormalizersTaskListView(TaskListView):
    template_name = "tasks/normalizers.html"
    plugin_type = "normalizer"
