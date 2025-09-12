from datetime import datetime, timezone

import django_filters
import recurrence
import structlog
from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, UpdateView
from django_filters.views import FilterView

from openkat.permissions import KATModelPermissionRequiredMixin
from tasks.models import NewSchedule, Task, TaskStatus
from tasks.new_tasks import run_schedule, run_task


class TaskFilter(django_filters.FilterSet):
    data = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = Task
        fields = ["organization", "data", "status"]


class TaskListView(FilterView):
    template_name = "task_list.html"
    fields = ["enabled_plugins"]
    model = Task
    ordering = ["-created_at"]
    paginate_by = settings.VIEW_DEFAULT_PAGE_SIZE
    filterset_class = TaskFilter

    def get_queryset(self):
        qs = super().get_queryset()

        if not self.request.user.can_access_all_organizations:
            qs = qs.filter(organization__members__user=self.request.user)

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
            {"url": reverse("task_detail", kwargs={"pk": self.get_object().id}), "text": _("Task details")},
        ]

        return context


class TaskForm(ModelForm):
    class Meta:
        model = Task
        fields = ["organization", "data"]

    def clean(self):
        cleaned_data = super().clean()

        logger = structlog.get_logger(__name__)
        logger.info(cleaned_data)
        if cleaned_data["data"]["plugin_id"] is None:
            raise ValidationError("Plugin ID cannot be blank.")

        return cleaned_data

    def save(self, *args, **kwargs):
        result = super().save(*args, **kwargs)
        run_task(self.instance)

        return result


class TaskCreateView(KATModelPermissionRequiredMixin, CreateView):
    model = Task
    template_name = "task_form.html"
    form_class = TaskForm

    def get_initial(self):
        initial = super().get_initial()
        initial["data"] = {"plugin_id": None, "input_data": []}

        if self.request.method == "GET" and "plugin_id" in self.request.GET:
            initial["data"]["plugin_id"] = self.request.GET.get("plugin_id")

        if self.request.method == "GET" and "input_data" in self.request.GET:
            initial["data"]["plugin_id"] = self.request.GET.getlist("input_data")

        return initial

    def get_success_url(self, **kwargs):
        redirect_url = self.get_form().data.get("current_url")

        if redirect_url and url_has_allowed_host_and_scheme(redirect_url, allowed_hosts=None):
            return redirect_url

        return reverse_lazy("new_task_list")


class TaskRescheduleView(PermissionRequiredMixin, View):
    permission_required = ("tasks.add_tasks",)

    def post(self, request, task_id, *args, **kwargs):
        run_task(Task.objects.get(pk=task_id))

        return redirect(reverse("new_task_list"))


class TaskCancelView(PermissionRequiredMixin, View):
    permission_required = ("tasks.change_tasks",)

    def post(self, request, task_id, *args, **kwargs):
        Task.objects.get(pk=task_id).cancel()

        return redirect(reverse("new_task_list"))


class NewScheduleFilter(django_filters.FilterSet):
    plugin__plugin_id = django_filters.CharFilter(label="Plugin", lookup_expr="icontains")
    input = django_filters.CharFilter(label="Input", lookup_expr="icontains")

    class Meta:
        model = NewSchedule
        fields = ["organization", "plugin__plugin_id", "input", "enabled", "object_set"]


class ScheduleListView(FilterView):
    template_name = "schedule_list.html"
    model = NewSchedule
    ordering = ["-id"]
    paginate_by = settings.VIEW_DEFAULT_PAGE_SIZE
    filterset_class = NewScheduleFilter

    def get_queryset(self):
        qs = super().get_queryset()

        if not self.request.user.can_access_all_organizations:
            qs = qs.filter(organization__members__user=self.request.user)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"url": reverse("schedule_list"), "text": _("Schedules")}]

        return context


class NewScheduleForm(ModelForm):
    class Meta:
        model = NewSchedule
        fields = ["enabled", "recurrences", "object_set"]


class ScheduleDetailView(DetailView):
    template_name = "schedule.html"
    model = NewSchedule

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {"url": reverse("schedule_list"), "text": _("Schedules")},
            {"url": reverse("schedule_detail", kwargs={"pk": self.get_object().id}), "text": _("Schedule details")},
        ]
        context["form"] = NewScheduleForm

        return context


class ScheduleCreateView(KATModelPermissionRequiredMixin, CreateView):
    model = NewSchedule
    fields = ["plugin", "object_set", "organization", "recurrences", "enabled"]
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

    def get_success_url(self, **kwargs):
        redirect_url = self.get_form().data.get("current_url")

        if redirect_url and url_has_allowed_host_and_scheme(redirect_url, allowed_hosts=None):
            return redirect_url

        return reverse_lazy("schedule_list")


class ScheduleUpdateView(KATModelPermissionRequiredMixin, UpdateView):
    model = NewSchedule
    fields = ["enabled", "recurrences", "object_set"]

    def form_valid(self, form):
        result = super().form_valid(form)

        if self.object.enabled:
            return result

        # Plugin has been disabled, cancel all tasks related to the schedule
        for task in Task.objects.filter(
            new_schedule=self.object,
            status__in=[TaskStatus.PENDING, TaskStatus.QUEUED, TaskStatus.RUNNING, TaskStatus.DISPATCHED],
        ):
            task.cancel()

        return result

    def form_invalid(self, form):
        return redirect(reverse("schedule_list"))

    def get_success_url(self, **kwargs):
        redirect_url = self.get_form().data.get("current_url")

        if redirect_url and url_has_allowed_host_and_scheme(redirect_url, allowed_hosts=None):
            return redirect_url

        return reverse_lazy("schedule_list")


class ScheduleDeleteView(KATModelPermissionRequiredMixin, DeleteView):
    model = NewSchedule

    def form_invalid(self, form):
        return redirect(reverse("schedule_list"))

    def get_success_url(self, **kwargs):
        redirect_url = self.get_form().data.get("current_url")

        if redirect_url and url_has_allowed_host_and_scheme(redirect_url, allowed_hosts=None):
            return redirect_url

        return reverse_lazy("schedule_list")


class ScheduleRunView(PermissionRequiredMixin, View):
    permission_required = ("schedules.add_newschedules",)

    def post(self, request, schedule_id, *args, **kwargs):
        run_schedule(NewSchedule.objects.get(pk=schedule_id))

        return redirect(reverse("new_task_list"))
