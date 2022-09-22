import json
from requests import HTTPError
from django.http import HttpResponse
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.shortcuts import redirect
from django.views.generic import View
from django.views.generic.list import ListView
from django.http import FileResponse
from django_otp.decorators import otp_required
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
        response = HttpResponse(
            FileResponse(json.dumps(task_details)), content_type="application/json"
        )
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
    def setup(self, request, *args, **kwargs):
        self.task_type = None
        self.org: Organization = request.active_organization
        if self.org:
            self.task_type = self.plugin_type + "-" + self.org.code
        else:
            error_message = _("Organization could not be found")
            messages.add_message(request, messages.ERROR, error_message)
        return super().setup(request, *args, **kwargs)

    def get_queryset(self):
        if self.task_type:
            try:
                queryset = client.list_tasks(self.task_type, limit=self.paginate_by)
                return queryset.results
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
    paginate_by = TASK_LIMIT
    plugin_type = "boefje"


@class_view_decorator(otp_required)
class NormalizersTaskListView(TaskListView):
    template_name = "tasks/normalizers.html"
    paginate_by = TASK_LIMIT
    plugin_type = "normalizer"
