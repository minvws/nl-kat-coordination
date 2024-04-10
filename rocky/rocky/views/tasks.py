from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic.list import ListView

from rocky.paginator import RockyPaginator
from rocky.views.page_actions import PageActionsView
from rocky.views.scheduler import SchedulerView


class TaskListView(SchedulerView, ListView, PageActionsView):
    paginator_class = RockyPaginator
    paginate_by = 2

    def get_queryset(self):
        return self.get_task_list()

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
