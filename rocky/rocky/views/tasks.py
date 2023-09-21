import uuid
from datetime import datetime
from enum import Enum

from account.mixins import OrganizationView
from django.contrib import messages
from django.http import FileResponse, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic.list import ListView
from katalogus.views.mixins import BoefjeMixin, NormalizerMixin
from requests import HTTPError

from rocky.scheduler import BadRequestError, ConflictError, TooManyRequestsError, client

TASK_LIMIT = 50


class PageActions(Enum):
    RESCHEDULE_TASK = "reschedule_task"


class DownloadTaskDetail(OrganizationView):
    def get(self, request, *args, **kwargs):
        task_id = kwargs["task_id"]
        filename = "task_" + task_id + ".json"
        task_details = client.get_task_details(task_id)
        if not self.is_task_id(task_id) or "detail" in task_details:
            return self.show_error_message()
        response = HttpResponse(FileResponse(task_details.json()), content_type="application/json")
        response["Content-Disposition"] = "attachment; filename=" + filename
        return response

    def is_task_id(self, task_id):
        forbidden_chars = ["/", ".", " "]
        for char in forbidden_chars:
            return char not in str(task_id)

    def show_error_message(self):
        error_message = _("Task details not found.")
        messages.add_message(self.request, messages.ERROR, error_message)
        return redirect(reverse("task_list", kwargs={"organization_code": self.organization.code}))


class TaskListView(OrganizationView, ListView):
    paginate_by = 20

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
            task = client.get_task_details(task_id)

            # TODO: Consistent UUID-parsing across services https://github.com/minvws/nl-kat-coordination/issues/1451
            new_id = uuid.uuid4()

            task.p_item.id = new_id
            task.p_item.data.id = new_id

            try:
                client.push_task(f"{task.type}-{self.organization.code}", task.p_item)
            except TooManyRequestsError:
                error_message = _("Task queue is full, please try again later.")
                messages.add_message(self.request, messages.ERROR, error_message)
                return
            except ConflictError:
                error_message = _("Task already queued.")
                messages.add_message(self.request, messages.ERROR, error_message)
                return
            except BadRequestError:
                error_message = _("Task is invalid.")
                messages.add_message(self.request, messages.ERROR, error_message)
                return

            success_message = (
                "Your task is scheduled and will soon be started in the background. \n "
                "Results will be added to the object list when they are in. "
                "It may take some time, a refresh of the page may be needed to show the results."
            )
            messages.add_message(self.request, messages.SUCCESS, success_message)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
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
