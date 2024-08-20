from typing import Any

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic.list import ListView
from httpx import HTTPError
from tools.forms.scheduler import TaskFilterForm

from rocky.paginator import RockyPaginator
from rocky.scheduler import LazyTaskList, SchedulerError, scheduler_client
from rocky.views.page_actions import PageActionsView
from rocky.views.scheduler import SchedulerView


class SchedulerListView(ListView):
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        try:
            return super().get_context_data(**kwargs)
        except SchedulerError as error:
            messages.error(self.request, error.message)
        return {}


class TaskListView(SchedulerView, SchedulerListView, PageActionsView):
    paginator_class = RockyPaginator
    paginate_by = 20
    context_object_name = "task_list"

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
        context["stats"] = self.get_task_statistics()
        context["breadcrumbs"] = [
            {
                "url": reverse("task_list", kwargs={"organization_code": self.organization.code}),
                "text": _("Tasks"),
            },
        ]
        return context


class BoefjesTaskListView(TaskListView):
    template_name = "tasks/boefjes.html"
    task_type = "boefje"


class NormalizersTaskListView(TaskListView):
    template_name = "tasks/normalizers.html"
    task_type = "normalizer"


class AllTaskListView(SchedulerListView, PageActionsView):
    paginator_class = RockyPaginator
    paginate_by = 20
    context_object_name = "task_list"
    client = scheduler_client(None)

    # def get_queryset(self):
    #     return self.get_task_list()

    def get_queryset(self):
        task_type = self.request.GET.get("type", self.task_type)
        # status = self.request.GET.get("scan_history_status", "") or None
        # input_ooi = self.request.GET.get("scan_history_search", "") or None
        self.schedulers = [f"{task_type}-{o.code}" for o in self.request.user.organizations]

        # def get_form_data(self) -> dict[str, Any]:
        form_data = TaskFilterForm(self.request.GET).data.dict()
        kwargs = {k: v for k, v in form_data.items() if v}

        # def get_task_filter_form(self) -> TaskFilterForm:
        #     return
        # if self.request.GET.get("scan_history_from"):
        #     min_created_at = datetime.strptime(self.request.GET.get("scan_history_from"), "%Y-%m-%d")
        # else:
        #     min_created_at = None
        # if self.request.GET.get("scan_history_to"):
        #     max_created_at = datetime.strptime(self.request.GET.get("scan_history_to"), "%Y-%m-%d")
        # else:
        #     max_created_at = None

        try:
            return LazyTaskList(
                self.client,
                task_type=task_type,
                filters={"filters": [{"column": "scheduler_id", "operator": "in", "value": self.schedulers}]},
                **kwargs,
            )

        except HTTPError:
            error_message = _("Fetching tasks failed: no connection with scheduler")
            messages.add_message(self.request, messages.ERROR, error_message)
            return []

    def post(self, request, *args, **kwargs):
        self.handle_page_action(request.POST["action"])
        return redirect(request.path)

    # def post(self, request, *args, **kwargs):
    #     try:
    #         if self.action == self.RESCHEDULE_TASK:
    #             task_id = self.request.POST.get("task_id", "")
    #             self.reschedule_task(task_id)
    #     except HTTPError as exc:
    #         message = f"HTTP error for {exc.request.url} - {exc}"
    #         messages.error(request, message)
    #     except SchedulerError as error:
    #         messages.error(request, error.message)
    #     return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # context["task_filter_form"] = self.get_task_filter_form()
        context["stats"] = self.client.get_combined_schedulers_stats(scheduler_ids=self.schedulers)
        # context["breadcrumbs"] = [
        #     {
        #         "url": reverse("task_list", kwargs={"organization_code": self.organization.code}),
        #         "text": _("Tasks"),
        #     },
        # ]
        context["breadcrumbs"] = [
            {"url": reverse("all_task_list", kwargs={}), "text": _("All Tasks")},
        ]
        return context


class AllBoefjesTaskListView(AllTaskListView):
    template_name = "tasks/boefjes.html"
    task_type = "boefje"


class AllNormalizersTaskListView(AllTaskListView):
    template_name = "tasks/normalizers.html"
    task_type = "normalizer"
