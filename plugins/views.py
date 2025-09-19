import django_filters
from django.conf import settings
from django.contrib import messages
from django.db.models import Q
from django.db.models.functions import Coalesce
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DeleteView, DetailView, UpdateView
from django_filters.views import FilterView

from openkat.models import Organization
from openkat.permissions import KATModelPermissionRequiredMixin
from plugins.models import EnabledPlugin, Plugin, PluginQuerySet, ScanLevel
from tasks.models import Task, TaskStatus


class PluginFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(label="Name", lookup_expr="icontains")
    plugin_id = django_filters.CharFilter(label="Plugin", lookup_expr="icontains")
    oci_image = django_filters.CharFilter(label="Image", lookup_expr="icontains")
    enabled = django_filters.BooleanFilter(label="Enabled")
    scan_level = django_filters.MultipleChoiceFilter(choices=ScanLevel.choices, label="Scan Level")

    class Meta:
        model = Plugin
        fields = ["name", "plugin_id", "oci_image", "enabled", "scan_level"]


class PluginListView(FilterView):
    template_name = "plugin_list.html"
    fields = ["enabled_plugins"]
    model = Plugin
    paginate_by = settings.VIEW_DEFAULT_PAGE_SIZE
    filterset_class = PluginFilter

    def get_queryset(self):
        plugins: PluginQuerySet = super().get_queryset()

        if not self.request.user.can_access_all_organizations:
            # TODO: multi organization filter
            organization = Organization.objects.filter(members__user=self.request.user).first()
            plugins = plugins.with_enabled(organization)
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
            {"url": reverse("plugin_detail", kwargs={"pk": self.get_object().id}), "text": _("Plugin details")},
        ]

        return context


class PluginIdDetailView(PluginDetailView):
    slug_url_kwarg = "plugin_id"
    slug_field = "plugin_id"


class PluginCreateView(KATModelPermissionRequiredMixin, CreateView):
    model = Plugin
    fields = ["plugin_id", "name", "description", "scan_level", "oci_image", "oci_arguments"]
    template_name = "plugin_form.html"

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

        return kwargs

    def form_invalid(self, form):
        return redirect(reverse("plugin_list"))

    def get_success_url(self, **kwargs):
        redirect_url = self.get_form().data.get("current_url")

        if redirect_url and url_has_allowed_host_and_scheme(redirect_url, allowed_hosts=None):
            return redirect_url

        return reverse_lazy("plugin_list")


class PluginUpdateView(PluginCreateView):
    model = Plugin
    fields = ["plugin_id", "name", "description", "scan_level", "oci_image", "oci_arguments"]
    template_name = "plugin_settings.html"

    def form_invalid(self, form):
        return reverse("plugin_detail", kwargs={"pk": self.object.id})

    def get_success_url(self, **kwargs):
        redirect_url = self.get_form().data.get("current_url")

        if redirect_url and url_has_allowed_host_and_scheme(redirect_url, allowed_hosts=None):
            return redirect_url

        return reverse("plugin_detail", kwargs={"pk": self.object.id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {"url": reverse("plugin_list"), "text": _("Plugins")},
            {"url": reverse("plugin_detail", kwargs={"pk": self.object.id}), "text": _("Plugin details")},
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
            data__plugin_id=self.object.plugin.id,
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
