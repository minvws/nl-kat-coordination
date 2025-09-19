import datetime
from datetime import UTC, datetime

import django_filters
import recurrence
from django import forms
from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.forms import ModelForm
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, UpdateView
from django_filters.views import FilterView

from openkat.models import Organization
from openkat.permissions import KATModelPermissionRequiredMixin
from plugins.models import Plugin
from tasks.models import ObjectSet, Schedule, Task, TaskStatus
from tasks.tasks import rerun_task, run_plugin_task, run_schedule


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
            {"url": reverse("task_list"), "text": _("Plugins")},
            {"url": reverse("task_detail", kwargs={"pk": self.get_object().id}), "text": _("Task details")},
        ]

        return context


class TaskForm(ModelForm):
    plugin = forms.ModelChoiceField(Plugin.objects.with_enabled().filter(enabled=True))
    # input_data = forms.ModelMultipleChoiceField(Asset.objects.all(), required=False)  #TODO: fix

    class Meta:
        model = Task
        fields = ["organization"]

    def save(self, *args, **kwargs):
        plugin = self.cleaned_data["plugin"]

        if self.cleaned_data["organization"] is None:
            # TODO: handle..
            organization = Organization.objects.first()
        else:
            organization = self.cleaned_data["organization"]

        if not plugin.enabled_for(organization):
            raise ValueError(f"Plugin not enabled for organization {organization.name}")

        pks = list(self.cleaned_data["input_data"].values_list("value", flat=True))
        input_data = set()

        if pks:
            now = datetime.now(UTC)
            # TODO: fix
            # octopoes: OctopoesService = settings.OCTOPOES_FACTORY(organization.code).octopoes
            # scan_profiles = octopoes.scan_profile_repository.get_bulk(set(pks), now)
            #
            # for profile in scan_profiles:
            #     if profile.level.value < plugin.scan_level or str(profile.reference) not in pks:
            #         continue
            #
            #     if profile.reference.class_type == Hostname:
            #         input_data.add(profile.reference.tokenized.name)
            #         continue
            #
            #     if profile.reference.class_type in [IPAddressV4, IPAddressV6]:
            #         input_data.add(str(profile.reference.tokenized.address))
            #         continue
            #
            #     input_data.add(str(profile.reference))

        if not input_data and plugin.consumed_types():
            raise ValueError("No matching input objects found for plugin requiring input objects")

        return run_plugin_task(
            plugin.plugin_id,
            None if self.cleaned_data["organization"] is None else self.cleaned_data["organization"].code,
            list(input_data),
            batch=False,
        )


class TaskCreateView(KATModelPermissionRequiredMixin, CreateView):
    model = Task
    template_name = "task_form.html"
    form_class = TaskForm

    def get_initial(self):
        initial = super().get_initial()

        if self.request.method == "GET" and "plugin_id" in self.request.GET:
            initial["plugin_id"] = self.request.GET.get("plugin_id")

        return initial

    def get_success_url(self, **kwargs):
        redirect_url = self.get_form().data.get("current_url")

        if redirect_url and url_has_allowed_host_and_scheme(redirect_url, allowed_hosts=None):
            return redirect_url

        return reverse_lazy("task_list")


class TaskRescheduleView(PermissionRequiredMixin, View):
    permission_required = ("tasks.add_tasks",)

    def post(self, request, task_id, *args, **kwargs):
        rerun_task(Task.objects.get(pk=task_id))

        return redirect(reverse("task_list"))


class TaskCancelView(PermissionRequiredMixin, View):
    permission_required = ("tasks.change_tasks",)

    def post(self, request, task_id, *args, **kwargs):
        Task.objects.get(pk=task_id).cancel()

        return redirect(reverse("task_list"))


class ScheduleFilter(django_filters.FilterSet):
    plugin__plugin_id = django_filters.CharFilter(label="Plugin", lookup_expr="icontains")
    input = django_filters.CharFilter(label="Input", lookup_expr="icontains")

    class Meta:
        model = Schedule
        fields = ["organization", "plugin__plugin_id", "input", "enabled", "object_set"]


class ScheduleListView(FilterView):
    template_name = "schedule_list.html"
    model = Schedule
    ordering = ["-id"]
    paginate_by = settings.VIEW_DEFAULT_PAGE_SIZE
    filterset_class = ScheduleFilter

    def get_queryset(self):
        qs = super().get_queryset()

        if not self.request.user.can_access_all_organizations:
            qs = qs.filter(organization__members__user=self.request.user)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"url": reverse("schedule_list"), "text": _("Schedules")}]

        return context


class ScheduleForm(ModelForm):
    class Meta:
        model = Schedule
        fields = ["enabled", "recurrences", "object_set"]


class ScheduleDetailView(DetailView):
    template_name = "schedule.html"
    model = Schedule

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {"url": reverse("schedule_list"), "text": _("Schedules")},
            {"url": reverse("schedule_detail", kwargs={"pk": self.get_object().id}), "text": _("Schedule details")},
        ]
        context["form"] = ScheduleForm

        return context


class ScheduleCreateView(KATModelPermissionRequiredMixin, CreateView):
    model = Schedule
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
                dtstart=datetime.now(UTC),
            )

        self.object.save()
        return super().form_valid(form)

    def get_success_url(self, **kwargs):
        redirect_url = self.get_form().data.get("current_url")

        if redirect_url and url_has_allowed_host_and_scheme(redirect_url, allowed_hosts=None):
            return redirect_url

        return reverse_lazy("schedule_list")


class ScheduleUpdateView(KATModelPermissionRequiredMixin, UpdateView):
    model = Schedule
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
    model = Schedule

    def form_invalid(self, form):
        return redirect(reverse("schedule_list"))

    def get_success_url(self, **kwargs):
        redirect_url = self.get_form().data.get("current_url")

        if redirect_url and url_has_allowed_host_and_scheme(redirect_url, allowed_hosts=None):
            return redirect_url

        return reverse_lazy("schedule_list")


class ScheduleRunView(PermissionRequiredMixin, View):
    permission_required = ("schedules.add_schedules",)

    def post(self, request, schedule_id, *args, **kwargs):
        run_schedule(Schedule.objects.get(pk=schedule_id))

        return redirect(reverse("task_list"))


class ObjectSetFilter(django_filters.FilterSet):
    object_query = django_filters.CharFilter(label="Object Query", lookup_expr="icontains")
    name = django_filters.CharFilter(label="Name", lookup_expr="icontains")
    description = django_filters.CharFilter(label="Description", lookup_expr="icontains")

    class Meta:
        model = ObjectSet
        fields = ["name", "description", "object_query"]


class ObjectSetListView(FilterView):
    template_name = "object_set_list.html"
    model = ObjectSet
    paginate_by = settings.VIEW_DEFAULT_PAGE_SIZE
    filterset_class = ObjectSetFilter

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"url": reverse("object_list"), "text": _("Objects")}]

        return context


class ObjectSetDetailView(DetailView):
    template_name = "object_set.html"
    model = ObjectSet

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {"url": reverse("object_list"), "text": _("Objects")},
            {"url": reverse("object_set_detail", kwargs={"pk": self.get_object().id}), "text": _("Object Set Detail")},
        ]

        now = datetime.datetime.now(UTC)
        obj = self.get_object()

        # TODO: handle...
        org = Organization.objects.first()

        if obj.object_query:
            # TODO: fix
            # try:
            #     query = Query.from_path(obj.object_query)
            # except (ValueError, TypeNotFound):
            #     raise ValueError(f"Invalid query: {obj.object_query}")
            #
            # pk = Aliased(query.result_type, field="primary_key")
            # objects = connector.octopoes.ooi_repository.query(
            #     query.find(pk).where(query.result_type, primary_key=pk).limit(10), now,
            # )
            #
            # context["preview"] = [obj[1] for obj in objects]
            context["preview_organization"] = org
        else:
            context["preview"] = None
            context["preview_organization"] = None

        return context


class ObjectSetCreateView(KATModelPermissionRequiredMixin, CreateView):
    model = ObjectSet
    fields = ["name", "all_objects", "object_query", "description", "dynamic"]
    template_name = "object_set_form.html"

    def get_success_url(self, **kwargs):
        redirect_url = self.get_form().data.get("current_url")

        if redirect_url and url_has_allowed_host_and_scheme(redirect_url, allowed_hosts=None):
            return redirect_url

        return reverse_lazy("object_set_list")


class ObjectSetDeleteView(KATModelPermissionRequiredMixin, DeleteView):
    model = ObjectSet

    def form_invalid(self, form):
        return redirect(reverse("object_set_list"))

    def get_success_url(self, **kwargs):
        redirect_url = self.get_form().data.get("current_url")

        if redirect_url and url_has_allowed_host_and_scheme(redirect_url, allowed_hosts=None):
            return redirect_url

        return reverse_lazy("object_set_list")
