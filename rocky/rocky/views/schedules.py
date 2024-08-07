from typing import Any

from django.contrib import messages
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic.list import ListView

from rocky.paginator import RockyPaginator
from rocky.scheduler import SchedulerError
from rocky.views.scheduler import SchedulerView


class SchedulerListView(ListView):
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        try:
            return super().get_context_data(**kwargs)
        except SchedulerError as error:
            messages.error(self.request, error.message)
        return {}


class SchedulesListView(SchedulerView, SchedulerListView):
    paginator_class = RockyPaginator
    paginate_by = 20
    context_object_name = "task_schedules"
    template_name = "schedules/task_schedules.html"

    def get_queryset(self):
        return self.get_task_schedules()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["task_filter_form"] = self.get_task_filter_form()
        context["stats"] = self.get_task_statistics()
        context["breadcrumbs"] = [
            {
                "url": reverse("task_list", kwargs={"organization_code": self.organization.code}),
                "text": _("Tasks"),
            },
            {
                "url": reverse("task_schedules", kwargs={"organization_code": self.organization.code}),
                "text": _("Schedules"),
            },
        ]
        return context
