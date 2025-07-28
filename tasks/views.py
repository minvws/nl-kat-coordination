from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, ListView

from tasks.models import Task


class TaskListView(ListView):
    template_name = "task_list.html"
    fields = ["enabled_plugins"]
    model = Task
    ordering = ["-created_at"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"url": reverse("plugin_list"), "text": _("Tasks")}]

        return context


class TaskDetailView(DetailView):
    template_name = "task.html"
    model = Task

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {"url": reverse("plugin_list"), "text": _("Plugins")},
            {"url": reverse("plugin_detail", kwargs={"pk": self.get_object().id}), "text": _("Plugin Detail")},
        ]

        return context
