from datetime import datetime, timezone

import recurrence
from django.conf import settings
from django.forms import ModelForm
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from tasks.models import NewSchedule, Task
from tasks.new_tasks import rerun_task, run_schedule


class TaskListView(ListView):
    template_name = "task_list.html"
    fields = ["enabled_plugins"]
    model = Task
    ordering = ["-created_at"]
    paginate_by = settings.VIEW_DEFAULT_PAGE_SIZE

    def get_queryset(self):
        qs = super().get_queryset()

        if "schedule_id" in self.request.GET:
            qs = qs.filter(new_schedule__id=self.request.GET["schedule_id"])

        return qs

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


class TaskRescheduleView(View):
    def post(self, request, task_id, *args, **kwargs):
        rerun_task(Task.objects.get(pk=task_id))

        return redirect(reverse("new_task_list"))


class ScheduleListView(ListView):
    template_name = "schedule_list.html"
    model = NewSchedule
    ordering = ["-id"]
    paginate_by = settings.VIEW_DEFAULT_PAGE_SIZE

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"url": reverse("schedule_list"), "text": _("Schedules")}]

        return context


class NewScheduleForm(ModelForm):
    class Meta:
        model = NewSchedule
        fields = ["enabled", "recurrences", "input"]


class ScheduleDetailView(DetailView):
    template_name = "schedule.html"
    model = NewSchedule

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {"url": reverse("schedule_list"), "text": _("Schedules")},
            {"url": reverse("schedule_detail", kwargs={"pk": self.get_object().id}), "text": _("Schedule Detail")},
        ]
        context["form"] = NewScheduleForm

        return context


class ScheduleCreateView(CreateView):
    model = NewSchedule
    fields = ["plugin", "input", "organization", "recurrences", "enabled"]
    template_name = "schedule_form.html"

    def form_valid(self, form):
        self.object = form.save()

        if self.object.recurrences and str(self.object.recurrences):
            return super().form_valid(form)
        if self.object.plugin and self.object.plugin.recurrences and str(self.object.plugin.recurrences):
            self.object.recurrences = self.object.plugin.recurrences
        else:
            self.object.recurrences = recurrence.Recurrence(
                rrules=[recurrence.Rule(recurrence.DAILY)],  # Daily scheduling is the default for plugins
                dtstart=datetime.now(timezone.utc),
            )

        self.object.save()
        return super().form_valid(form)

    def form_invalid(self, form):
        return redirect(reverse("schedule_list"))

    def get_success_url(self, **kwargs):
        redirect_url = self.get_form().data.get("current_url")

        if redirect_url and url_has_allowed_host_and_scheme(redirect_url, allowed_hosts=None):
            return redirect_url

        return reverse_lazy("schedule_list")


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


class ScheduleDeleteView(DeleteView):
    model = NewSchedule

    def form_invalid(self, form):
        return redirect(reverse("schedule_list"))

    def get_success_url(self, **kwargs):
        redirect_url = self.get_form().data.get("current_url")

        if redirect_url and url_has_allowed_host_and_scheme(redirect_url, allowed_hosts=None):
            return redirect_url

        return reverse_lazy("schedule_list")


class ScheduleRunView(View):
    def post(self, request, schedule_id, *args, **kwargs):
        run_schedule(NewSchedule.objects.get(pk=schedule_id))

        return redirect(reverse("new_task_list"))
