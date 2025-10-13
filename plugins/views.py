from typing import Any

import django_filters
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, QuerySet
from django.db.models.functions import Coalesce
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DeleteView, DetailView, UpdateView
from django_filters.views import FilterView
from djangoql.exceptions import DjangoQLParserError
from djangoql.queryset import apply_search

from objects.models import FindingType
from openkat.mixins import OrganizationFilterMixin
from openkat.models import Organization
from openkat.permissions import KATModelPermissionRequiredMixin
from plugins.models import BusinessRule, EnabledPlugin, Plugin, PluginQuerySet, ScanLevel
from tasks.models import Task, TaskStatus
from tasks.views import TaskFilter


class PluginFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(label="Name", lookup_expr="icontains", widget=forms.TextInput())
    oci_image = django_filters.CharFilter(label="Container image", lookup_expr="icontains", widget=forms.TextInput())
    scan_level = django_filters.ChoiceFilter(label="Scan level", choices=ScanLevel.choices)
    enabled = django_filters.ChoiceFilter(label="State", choices=((True, "Enabled"), (False, "Disabled")))

    class Meta:
        model = Plugin
        fields = ["name", "oci_image", "scan_level", "enabled"]


class PluginVariantFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(label="Name", lookup_expr="icontains", widget=forms.TextInput())
    scan_level = django_filters.ChoiceFilter(label="Scan level", choices=ScanLevel.choices)

    class Meta:
        model = Plugin
        fields = ["name", "scan_level"]


class PluginListView(OrganizationFilterMixin, FilterView):
    template_name = "plugin_list.html"
    fields = ["enabled_plugins"]
    model = Plugin
    paginate_by = settings.VIEW_DEFAULT_PAGE_SIZE
    filterset_class = PluginFilter

    def get_queryset(self) -> QuerySet:
        plugins: PluginQuerySet = Plugin.objects.all()
        organization_codes = self.request.GET.getlist("organization")

        if not self.request.user.can_access_all_organizations:
            organizations = Organization.objects.filter(members__user=self.request.user)
        else:
            organizations = Organization.objects.all()

        if organization_codes:
            organizations = organizations.filter(code__in=organization_codes)

            if organizations.count() == 1:
                plugins = plugins.with_enabled(organizations.first())
            else:
                plugins = plugins.with_enabled(None)
        elif not self.request.user.can_access_all_organizations:
            plugins = plugins.with_enabled(organizations.first())
        else:
            plugins = plugins.with_enabled(None)

        order_by = self.request.GET.get("order_by", "name")
        sorting_order = self.request.GET.get("sorting_order", "asc")

        if order_by and sorting_order == "desc":
            return plugins.order_by(f"-{order_by}")

        return plugins.order_by(order_by)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"url": reverse("plugin_list"), "text": _("Plugins")}]
        context["order_by"] = self.request.GET.get("order_by")
        context["sorting_order"] = self.request.GET.get("sorting_order", "asc")
        context["sorting_order_class"] = "ascending" if context["sorting_order"] == "asc" else "descending"

        # Determine if enable/disable actions should be allowed
        organization_codes = self.request.GET.getlist("organization")
        if organization_codes:
            organizations = Organization.objects.filter(code__in=organization_codes)
            context["enable_disable_allowed"] = organizations.count() == 1
            if organizations.count() == 1:
                context["selected_organization"] = organizations.first()
        else:
            context["enable_disable_allowed"] = True
            if not self.request.user.can_access_all_organizations:
                context["selected_organization"] = Organization.objects.filter(members__user=self.request.user).first()

        return context


class PluginDetailView(DetailView):
    template_name = "plugin.html"
    model = Plugin

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(Q(enabled_plugins__organization=None) | Q(enabled_plugins__isnull=True))
            .annotate(
                enabled=Coalesce("enabled_plugins__enabled", False), enabled_id=Coalesce("enabled_plugins__id", None)
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {"url": reverse("plugin_list"), "text": _("Plugins")},
            {"url": reverse("plugin_detail", kwargs={"pk": self.object.pk}), "text": _("Plugin details")},
        ]

        return context


class PluginIdDetailView(PluginDetailView):
    slug_url_kwarg = "plugin_id"
    slug_field = "plugin_id"


class PluginScansDetailView(PluginDetailView):
    template_name = "plugin_scans.html"
    filterset_class = TaskFilter
    paginate_by = settings.VIEW_DEFAULT_PAGE_SIZE

    def get_tasks(self):
        return Task.objects.filter(data__plugin_id=self.get_object().plugin_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filterset = self.filterset_class(self.request.GET, queryset=self.get_tasks())
        context["filter"] = filterset
        context["task_list"] = filterset.qs.order_by("-ended_at")
        return context


class PluginVariantsDetailView(PluginDetailView):
    template_name = "plugin_variants.html"
    filterset_class = PluginVariantFilter
    paginate_by = settings.VIEW_DEFAULT_PAGE_SIZE

    def get_variants(self):
        return Plugin.objects.filter(oci_image=self.get_object().oci_image)

    def filter_variants(self, filterset):
        variants = (
            filterset.qs.filter(Q(enabled_plugins__organization=None) | Q(enabled_plugins__isnull=True))
            .annotate(
                enabled=Coalesce("enabled_plugins__enabled", False), enabled_id=Coalesce("enabled_plugins__id", None)
            )
            .order_by("name")
        )
        return variants

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filterset = self.filterset_class(self.request.GET, queryset=self.get_variants())
        context["filter"] = filterset
        context["variants"] = self.filter_variants(filterset)
        return context


class PluginCreateView(KATModelPermissionRequiredMixin, CreateView):
    model = Plugin
    fields = ["plugin_id", "name", "consumes", "description", "scan_level", "batch_size", "oci_image", "oci_arguments"]
    template_name = "plugin_form.html"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["description"].widget.attrs["rows"] = 3
        return form

    def get_form_kwargs(self):
        if self.request.method == "POST" and "plugin_id" in self.request.GET:
            if "duplicate" in self.request.GET and self.request.GET["duplicate"]:
                # Do not set self.object as we want to create a new plugin
                return super().get_form_kwargs()

            # Will perform an update instead of a Create
            self.object = Plugin.objects.get(pk=self.request.GET["plugin_id"])
            return super().get_form_kwargs()

        if "plugin_id" in self.request.GET:
            # Will provide the form with initial values from this plugin
            self.object = Plugin.objects.get(pk=self.request.GET["plugin_id"])

        kwargs = super().get_form_kwargs()

        # If we are duplicating a plugin, we should make sure a unique plugin id and name are chosen
        if "duplicate" in self.request.GET and self.request.GET["duplicate"]:
            kwargs["initial"]["plugin_id"] = None
            kwargs["initial"]["name"] = None

        # Pre-fill oci_arguments from query parameter (e.g., from file list "Add to plugin" button)
        if "oci_arguments" in self.request.GET:
            oci_arg = self.request.GET["oci_arguments"]
            if "initial" not in kwargs:
                kwargs["initial"] = {}
            kwargs["initial"]["oci_arguments"] = [oci_arg]

        return kwargs

    def form_invalid(self, form):
        return redirect(reverse("plugin_list"))

    def get_success_url(self, **kwargs):
        redirect_url = self.get_form().data.get("current_url")

        if redirect_url and url_has_allowed_host_and_scheme(redirect_url, allowed_hosts=None):
            return redirect_url

        return reverse_lazy("plugin_list")


class PluginUpdateView(KATModelPermissionRequiredMixin, UpdateView):
    model = Plugin
    fields = ["plugin_id", "name", "consumes", "description", "scan_level", "batch_size", "oci_image", "oci_arguments"]
    template_name = "plugin_settings.html"

    object: Plugin

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["description"].widget.attrs["rows"] = 3
        return form

    def form_invalid(self, form):
        return reverse("plugin_detail", kwargs={"pk": self.object.pk})

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(Q(enabled_plugins__organization=None) | Q(enabled_plugins__isnull=True))
            .annotate(
                enabled=Coalesce("enabled_plugins__enabled", False), enabled_id=Coalesce("enabled_plugins__id", None)
            )
        )

    def get_success_url(self, **kwargs):
        return reverse("plugin_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["plugin"] = self.object
        context["breadcrumbs"] = [
            {"url": reverse("plugin_list"), "text": _("Plugins")},
            {"url": reverse("plugin_detail", kwargs={"pk": self.object.pk}), "text": _("Plugin details")},
        ]

        return context


class PluginDeleteView(KATModelPermissionRequiredMixin, DeleteView):
    model = Plugin

    def form_invalid(self, form):
        return redirect(reverse("plugin_list"))

    def get_success_url(self, **kwargs):
        redirect_url = self.get_form().data.get("current_url")

        if redirect_url and url_has_allowed_host_and_scheme(redirect_url, allowed_hosts=None):
            return redirect_url

        return reverse_lazy("plugin_list")


class EnabledPluginView(KATModelPermissionRequiredMixin, CreateView):
    model = EnabledPlugin
    fields = ["enabled", "plugin", "organization"]
    template_name = "enable_disable_plugin.html"

    def form_invalid(self, form):
        return redirect(reverse("plugin_list"))

    def get_success_url(self, **kwargs):
        redirect_url = self.get_form().data.get("current_url")

        if redirect_url and url_has_allowed_host_and_scheme(redirect_url, allowed_hosts=None):
            return redirect_url

        return reverse_lazy("plugin_list")


class EnabledPluginUpdateView(KATModelPermissionRequiredMixin, UpdateView):
    model = EnabledPlugin
    fields = ["enabled"]
    template_name = "enable_disable_plugin.html"

    object: EnabledPlugin

    def form_invalid(self, form):
        return redirect(reverse("plugin_list"))

    def form_valid(self, form):
        result = super().form_valid(form)

        if self.object.enabled:
            messages.add_message(
                self.request, messages.SUCCESS, _("Plugin '{}' has been enabled.").format(self.object.plugin.name)
            )
            return result

        # Plugin has been disabled, cancel all tasks for this plugin and organization
        for task in Task.objects.filter(
            organization=self.object.organization,
            data__plugin_id=self.object.plugin.pk,
            status__in=[TaskStatus.PENDING, TaskStatus.QUEUED, TaskStatus.RUNNING, TaskStatus.DISPATCHED],
        ):
            task.cancel()

        messages.add_message(
            self.request, messages.SUCCESS, _("Plugin '{}' has been disabled.").format(self.object.plugin.name)
        )
        return result

    def get_success_url(self, **kwargs):
        redirect_url = self.get_form().data.get("current_url")

        if redirect_url and url_has_allowed_host_and_scheme(redirect_url, allowed_hosts=None):
            return redirect_url

        return reverse_lazy("plugin_list")


class BusinessRuleFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(label="Name", lookup_expr="icontains")
    enabled = django_filters.BooleanFilter(label="Enabled")
    object_type = django_filters.ModelChoiceFilter(
        label="Object Type", queryset=ContentType.objects.filter(app_label="objects")
    )

    class Meta:
        model = BusinessRule
        fields = ["name", "enabled", "object_type"]


class BusinessRuleListView(FilterView):
    model = BusinessRule
    template_name = "plugins/business_rule_list.html"
    context_object_name = "business_rules"
    filterset_class = BusinessRuleFilter
    paginate_by = 20
    ordering = ["-created_at"]

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"url": reverse("business_rule_list"), "text": _("Business Rules")}]

        return context


class BusinessRuleDetailView(DetailView):
    model = BusinessRule
    template_name = "plugins/business_rule_detail.html"
    context_object_name = "business_rule"

    object: BusinessRule

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"url": reverse("business_rule_list"), "text": _("Business Rules")}]
        context["matching_objects"] = []
        context["total_count"] = 0

        model_class = self.object.object_type.model_class()
        if model_class is None:
            context["query_error"] = f"Unknown object type: {self.object.object_type}"
            return context

        queryset = model_class.objects.all()
        context["matching_objects"] = []

        try:
            queryset = model_class.objects.all()
            context["matching_objects"] = apply_search(queryset, self.object.query)[:20]
        except DjangoQLParserError:
            try:
                context["matching_objects"] = queryset.raw(self.object.query)[:20]
            except Exception as e:
                context["query_error"] = str(e)
        except Exception as e:
            context["query_error"] = str(e)

        return context


class BusinessRuleForm(forms.ModelForm):
    finding_type_code = forms.CharField(max_length=100, help_text="Finding type code (e.g., KAT-WEBSERVER-NO-IPV6)")

    class Meta:
        model = BusinessRule
        fields = ["name", "description", "enabled", "object_type", "query", "finding_type_code"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3}), "query": forms.Textarea(attrs={"rows": 5})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filter object_type to only show objects from the "objects" app
        self.fields["object_type"].queryset = ContentType.objects.filter(app_label="objects")

        if self.instance and self.instance.pk:
            self.fields["finding_type_code"].initial = self.instance.finding_type_code

    def save(self, commit=True):
        instance = super().save(commit=False)
        finding_type_code = self.cleaned_data["finding_type_code"]
        FindingType.objects.get_or_create(code=finding_type_code)

        if commit:
            instance.save()
        return instance


class BusinessRuleCreateView(CreateView):
    model = BusinessRule
    form_class = BusinessRuleForm
    template_name = "plugins/business_rule_form.html"

    object: BusinessRule

    def get_success_url(self) -> str:
        return reverse("business_rule_detail", kwargs={"pk": self.object.pk})


class BusinessRuleUpdateView(UpdateView):
    model = BusinessRule
    form_class = BusinessRuleForm
    template_name = "plugins/business_rule_form.html"

    object: BusinessRule

    def get_success_url(self) -> str:
        return reverse("business_rule_detail", kwargs={"pk": self.object.pk})


class BusinessRuleDeleteView(DeleteView):
    model = BusinessRule
    success_url = reverse_lazy("business_rule_list")


class BusinessRuleToggleView(UpdateView):
    model = BusinessRule
    fields: list[str] = []

    object: BusinessRule

    def form_valid(self, form):
        self.object.enabled = not self.object.enabled
        self.object.save()

        if self.object.enabled:
            messages.success(self.request, _("Business rule '{}' has been enabled.").format(self.object.name))
        else:
            messages.success(self.request, _("Business rule '{}' has been disabled.").format(self.object.name))

        return redirect(self.get_success_url())

    def get_success_url(self):
        redirect_url = self.request.POST.get("current_url")

        if redirect_url and url_has_allowed_host_and_scheme(redirect_url, allowed_hosts=None):
            return redirect_url

        return reverse_lazy("business_rule_list")
