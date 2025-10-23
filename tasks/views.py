from datetime import UTC, datetime

import django_filters
import recurrence
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.db.models import OuterRef, Subquery
from django.db.models.fields.json import KeyTextTransform
from django.forms import ModelForm
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, UpdateView
from django_filters.views import FilterView

from objects.models import FindingType, Hostname, IPAddress
from openkat.mixins import OrganizationFilterMixin
from openkat.permissions import KATModelPermissionRequiredMixin
from plugins.models import Plugin
from tasks.models import ObjectSet, Schedule, Task, TaskStatus
from tasks.tasks import rerun_task, run_plugin_task, run_schedule


class TaskFilter(django_filters.FilterSet):
    data = django_filters.CharFilter(
        label="Input object", lookup_expr="icontains", widget=forms.TextInput(attrs={"autocomplete": "off"})
    )
    type = django_filters.ChoiceFilter(label="Task type", choices=[("plugin", "Plugin"), ("report", "Report")])

    class Meta:
        model = Task
        fields = ["status", "type", "data"]


class TaskListView(OrganizationFilterMixin, FilterView):
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
            qs = qs.filter(schedule__id=self.request.GET["schedule_id"])

        qs = qs.annotate(
            plugin_name=Subquery(
                Plugin.objects.filter(plugin_id=KeyTextTransform("plugin_id", OuterRef("data"))).values("name")
            )
        )

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"url": reverse("plugin_list"), "text": _("Tasks")}]

        return context


class TaskDetailView(OrganizationFilterMixin, DetailView):
    template_name = "task.html"
    model = Task

    object: Task

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["plugin"] = Plugin.objects.get(plugin_id=self.object.data["plugin_id"])
        context["breadcrumbs"] = [
            {"url": reverse("task_list"), "text": _("Plugins")},
            {"url": reverse("task_detail", kwargs={"pk": self.object.pk}), "text": _("Task details")},
        ]

        return context


class TaskForm(ModelForm):
    plugin = forms.ModelChoiceField(Plugin.objects.all())
    input_hostnames = forms.ModelMultipleChoiceField(Hostname.objects.all(), required=False)
    input_ips = forms.ModelMultipleChoiceField(IPAddress.objects.all(), required=False)

    class Meta:
        model = Task
        fields = ["organization"]

    def save(self, *args, **kwargs):
        plugin = self.cleaned_data["plugin"]

        # TODO: fix, ips, etc.
        input_hostnames = {str(model) for model in self.cleaned_data["input_hostnames"]}
        input_ips = {str(model) for model in self.cleaned_data["input_ips"]}

        if not input_hostnames and not input_ips and plugin.consumed_types():
            raise ValueError("No matching input objects found for plugin requiring input objects")

        return run_plugin_task(
            plugin.plugin_id,
            None if self.cleaned_data["organization"] is None else self.cleaned_data["organization"].code,
            list(input_hostnames) + list(input_ips),
            batch=False,
        )[0]


class TaskCreateView(KATModelPermissionRequiredMixin, CreateView):
    model = Task
    template_name = "task_form.html"
    form_class = TaskForm

    def get_initial(self):
        initial = super().get_initial()

        if self.request.method == "GET" and "plugin" in self.request.GET:
            initial["plugin"] = self.request.GET.get("plugin")

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


class TaskCancelAllView(PermissionRequiredMixin, View):
    permission_required = ("tasks.change_tasks",)

    def post(self, request, *args, **kwargs):
        organization_codes = request.GET.getlist("organization")  # Only cancel tasks for the filtered organizations
        query = Task.objects.filter(status__in=[TaskStatus.QUEUED, TaskStatus.PENDING])

        # Apply organization filter if present
        if organization_codes:
            query = query.filter(organization__code__in=organization_codes)
        elif not request.user.can_access_all_organizations:
            query = query.filter(organization__members__user=request.user)

        if query.count() == 0:
            messages.warning(request, _("No tasks found matching the criteria."))
            return redirect(reverse("task_list"))

        # Cancel tasks
        cancelled_count = 0
        for task in query:
            try:
                task.cancel()
                cancelled_count += 1
            except Exception as e:
                messages.error(
                    request, _("Failed to cancel task {task_id}: {error}").format(task_id=task.id, error=str(e))
                )

        messages.success(request, _("Successfully cancelled {count} task(s).").format(count=cancelled_count))

        redirect_url = reverse("task_list")

        if organization_codes:
            redirect_url += "?" + "&".join([f"organization={code}" for code in organization_codes])

        return redirect(redirect_url)


class ScheduleFilter(django_filters.FilterSet):
    plugin__plugin_id = django_filters.CharFilter(label="Plugin", lookup_expr="icontains")
    input = django_filters.CharFilter(label="Input", lookup_expr="icontains")
    enabled = django_filters.ChoiceFilter(label="State", choices=((True, "Enabled"), (False, "Disabled")))
    task_type = django_filters.ChoiceFilter(label="Task type", choices=[("plugin", "Plugin"), ("report", "Report")])

    class Meta:
        model = Schedule
        fields = ["plugin__plugin_id", "task_type", "object_set", "enabled"]


class ScheduleListView(OrganizationFilterMixin, FilterView):
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
    # Add finding types field for reports
    report_finding_types_choices = forms.MultipleChoiceField(
        required=False,
        label=_("Finding Types"),
        help_text=_("Select finding types to include in the report (only for report schedules)"),
    )

    class Meta:
        model = Schedule
        fields = ["enabled", "recurrences", "object_set", "report_name", "report_description"]
        widgets = {"report_description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Load finding types for the multi-select field
        try:
            finding_type_choices = [
                (ft.code, f"{ft.name or ft.code} ({ft.code})")
                for ft in FindingType.objects.all().order_by("name")
                if ft.code
            ]
            self.fields["report_finding_types_choices"].choices = finding_type_choices

            # Set initial values if instance exists
            if self.instance and self.instance.pk and self.instance.report_finding_types:
                self.initial["report_finding_types_choices"] = self.instance.report_finding_types
        except Exception:
            self.fields["report_finding_types_choices"].choices = []

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Save the finding types from the multi-select field
        if "report_finding_types_choices" in self.cleaned_data:
            instance.report_finding_types = list(self.cleaned_data["report_finding_types_choices"])

        if commit:
            instance.save()

        return instance


class ScheduleDetailView(OrganizationFilterMixin, DetailView):
    template_name = "schedule.html"
    model = Schedule

    object: Schedule

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {"url": reverse("schedule_list"), "text": _("Schedules")},
            {"url": reverse("schedule_detail", kwargs={"pk": self.object.pk}), "text": _("Schedule details")},
        ]
        context["form"] = ScheduleForm

        return context


class ScheduleCreateView(KATModelPermissionRequiredMixin, CreateView):
    model = Schedule
    fields = [
        "task_type",
        "plugin",
        "object_set",
        "organization",
        "recurrences",
        "enabled",
        "report_name",
        "report_description",
    ]
    template_name = "schedule_form.html"

    object: Schedule

    def get_form(self, form_class=None):
        form = super().get_form(form_class)

        # Add finding types field for reports
        finding_type_choices = [
            (ft.code, f"{ft.name or ft.code} ({ft.code})")
            for ft in FindingType.objects.all().order_by("name")
            if ft.code
        ]

        form.fields["report_finding_types"] = forms.MultipleChoiceField(
            required=False,
            label=_("Finding Types"),
            choices=finding_type_choices,
            help_text=_("Select finding types to include in the report (only for report schedules)"),
        )

        # Add widget for report_description
        form.fields["report_description"].widget = forms.Textarea(attrs={"rows": 3})

        return form

    def form_valid(self, form):
        self.object = form.save(commit=False)

        # Handle report finding types
        if "report_finding_types" in form.cleaned_data:
            self.object.report_finding_types = list(form.cleaned_data["report_finding_types"])

        # Set task_type based on whether plugin or report fields are filled
        if not self.object.task_type:
            if self.object.plugin:
                self.object.task_type = "plugin"
            elif self.object.report_name:
                self.object.task_type = "report"

        # Set default recurrence if not provided
        if self.object.recurrences and str(self.object.recurrences):
            self.object.save()
            return super().form_valid(form)

        if self.object.plugin and self.object.plugin.recurrences and str(self.object.plugin.recurrences):
            self.object.recurrences = self.object.plugin.recurrences
        else:
            self.object.recurrences = recurrence.Recurrence(
                rrules=[recurrence.Rule(recurrence.DAILY)],  # Daily scheduling is the default
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
    fields = ["enabled", "recurrences", "object_set", "report_name", "report_description"]
    template_name = "schedule_form.html"

    object: Schedule

    def get_form(self, form_class=None):
        form = super().get_form(form_class)

        # Add finding types field for reports
        finding_type_choices = [
            (ft.code, f"{ft.name or ft.code} ({ft.code})")
            for ft in FindingType.objects.all().order_by("name")
            if ft.code
        ]

        form.fields["report_finding_types"] = forms.MultipleChoiceField(
            required=False,
            label=_("Finding Types"),
            choices=finding_type_choices,
            initial=self.object.report_finding_types if self.object.report_finding_types else [],
            help_text=_("Select finding types to include in the report (only for report schedules)"),
        )

        # Add widget for report_description
        if "report_description" in form.fields:
            form.fields["report_description"].widget = forms.Textarea(attrs={"rows": 3})

        return form

    def form_valid(self, form):
        # Handle report finding types before saving
        if "report_finding_types" in form.cleaned_data:
            self.object.report_finding_types = list(form.cleaned_data["report_finding_types"])

        result = super().form_valid(form)

        if self.object.enabled:
            return result

        # Schedule has been disabled, cancel all tasks related to the schedule
        for task in Task.objects.filter(
            schedule=self.object, status__in=[TaskStatus.PENDING, TaskStatus.QUEUED, TaskStatus.RUNNING]
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
        redirect_url = self.request.POST.get("current_url")

        if redirect_url and url_has_allowed_host_and_scheme(redirect_url, allowed_hosts=None):
            return redirect_url

        return reverse_lazy("schedule_list")


class ScheduleRunView(PermissionRequiredMixin, View):
    permission_required = ("schedules.add_schedules",)

    def post(self, request, schedule_id, *args, **kwargs):
        run_schedule(Schedule.objects.get(pk=schedule_id), force=True)

        return redirect(reverse("task_list"))


class ObjectSetFilter(django_filters.FilterSet):
    object_query = django_filters.CharFilter(label="Object query", lookup_expr="icontains")
    name = django_filters.CharFilter(label="Name", lookup_expr="icontains")
    description = django_filters.CharFilter(label="Description", lookup_expr="icontains")

    class Meta:
        model = ObjectSet
        fields = ["name", "description", "object_query"]


class ObjectSetListView(OrganizationFilterMixin, FilterView):
    template_name = "object_set_list.html"
    model = ObjectSet
    paginate_by = settings.VIEW_DEFAULT_PAGE_SIZE
    filterset_class = ObjectSetFilter

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"url": reverse("object_set_list"), "text": _("Objects Sets")}]

        return context


class ObjectSetDetailView(OrganizationFilterMixin, DetailView):
    template_name = "object_set.html"
    model = ObjectSet
    PREVIEW_SIZE = 20

    object: ObjectSet

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {"url": reverse("object_set_list"), "text": _("Objects Sets")},
            {"url": reverse("object_set_detail", kwargs={"pk": self.object.pk}), "text": _("Object Set Detail")},
        ]

        if self.object.object_query is not None and self.object.dynamic is True:
            # TODO: check scan profiles?
            context["objects"] = self.object.get_query_objects()[: self.PREVIEW_SIZE]
        else:
            context["objects"] = None

        context["all_objects"] = self.object.object_type.model_class().objects.filter(pk__in=self.object.all_objects)

        return context


class ObjectSetForm(ModelForm):
    all_objects = forms.MultipleChoiceField(
        widget=forms.SelectMultiple(attrs={"size": "10"}),
        required=False,
        help_text="Select objects manually. These will be combined with objects from the query.",
    )

    class Meta:
        model = ObjectSet
        fields = ["name", "description", "object_type", "object_query", "all_objects", "dynamic"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3}), "object_query": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["object_type"].queryset = ContentType.objects.filter(app_label="objects")
        object_type = None

        if self.instance and self.instance.pk and self.instance.object_type:
            object_type = self.instance.object_type
        elif self.data.get("object_type"):
            object_type = ContentType.objects.filter(pk=self.data.get("object_type")).first()

        if object_type:
            model_class = object_type.model_class()
            if model_class:
                objects = model_class.objects.all()
                choices = [(obj.pk, str(obj)) for obj in objects]
                self.fields["all_objects"].choices = choices

                if self.instance and self.instance.all_objects:
                    self.initial["all_objects"] = [str(pk) for pk in self.instance.all_objects]
        else:
            self.fields["all_objects"].choices = []
            self.fields["all_objects"].help_text += " (Select an object type first to see available objects.)"

    def clean_all_objects(self):
        return [int(pk) for pk in self.cleaned_data.get("all_objects", [])]


class ObjectSetCreateView(KATModelPermissionRequiredMixin, CreateView):
    model = ObjectSet
    form_class = ObjectSetForm
    template_name = "object_set_form.html"

    def get_success_url(self, **kwargs):
        redirect_url = self.get_form().data.get("current_url")

        if redirect_url and url_has_allowed_host_and_scheme(redirect_url, allowed_hosts=None):
            return redirect_url

        return reverse_lazy("object_set_list")


class ObjectSetUpdateView(KATModelPermissionRequiredMixin, UpdateView):
    model = ObjectSet
    form_class = ObjectSetForm
    template_name = "object_set_form.html"

    object: ObjectSet

    def get_success_url(self, **kwargs):
        return reverse_lazy("object_set_detail", kwargs={"pk": self.object.pk})


class ObjectSetDeleteView(KATModelPermissionRequiredMixin, DeleteView):
    model = ObjectSet

    def form_invalid(self, form):
        return redirect(reverse("object_set_list"))

    def get_success_url(self, **kwargs):
        redirect_url = self.request.POST.get("current_url")

        if redirect_url and url_has_allowed_host_and_scheme(redirect_url, allowed_hosts=None):
            return redirect_url

        return reverse_lazy("object_set_list")
