from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, ListView, UpdateView

from tasks.models import Task, NewSchedule


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
            {"url": reverse("new_task_list"), "text": _("Plugins")},
            {"url": reverse("task_detail", kwargs={"pk": self.get_object().id}), "text": _("Task Detail")},
        ]

        return context


class ScheduleListView(ListView):
    template_name = "schedule_list.html"
    model = NewSchedule
    ordering = ["-id"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"url": reverse("schedule_list"), "text": _("Schedules")}]

        return context


class ScheduleDetailView(DetailView):
    template_name = "schedule.html"
    model = NewSchedule

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {"url": reverse("schedule_list"), "text": _("Schedules")},
            {"url": reverse("schedule_detail", kwargs={"pk": self.get_object().id}), "text": _("Schedule Detail")},
        ]

        return context


class ScheduleUpdateView(UpdateView):
    model = NewSchedule
    fields = ["enabled", "recurrences", "input"]

    def form_invalid(self, form):
        return redirect(reverse("schedule_list"))

    def get_success_url(self, **kwargs):
        redirect_url = self.get_form().data.get("current_url")

        if redirect_url and url_has_allowed_host_and_scheme(redirect_url, allowed_hosts=None):
            return redirect_url

        return reverse_lazy("schedule_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {"url": reverse("schedule_list"), "text": _("Plugins")},
            {"url": reverse("schedule_detail", kwargs={"pk": self.get_object().id}), "text": _("Schedule Detail")},
        ]

        return context
