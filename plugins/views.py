from django.conf import settings
from django.db.models import Q
from django.db.models.functions import Coalesce
from django.http import FileResponse
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from katalogus.worker.repository import get_local_repository
from plugins.models import EnabledPlugin, Plugin


class PluginListView(ListView):
    template_name = "plugin_list.html"
    fields = ["enabled_plugins"]
    model = Plugin
    paginate_by = settings.VIEW_DEFAULT_PAGE_SIZE

    def get_queryset(self):
        plugins = (
            super()
            .get_queryset()
            .filter(Q(enabled_plugins__organization=None) | Q(enabled_plugins__isnull=True))
            .annotate(
                enabled=Coalesce("enabled_plugins__enabled", False), enabled_id=Coalesce("enabled_plugins__id", None)
            )
        )
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
            {"url": reverse("plugin_detail", kwargs={"pk": self.get_object().id}), "text": _("Plugin Detail")},
        ]

        return context


class PluginIdDetailView(PluginDetailView):
    slug_url_kwarg = "plugin_id"
    slug_field = "plugin_id"


class PluginCreateView(CreateView):
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


class PluginDeleteView(DeleteView):
    model = Plugin

    def form_invalid(self, form):
        return redirect(reverse("plugin_list"))

    def get_success_url(self, **kwargs):
        redirect_url = self.get_form().data.get("current_url")

        if redirect_url and url_has_allowed_host_and_scheme(redirect_url, allowed_hosts=None):
            return redirect_url

        return reverse_lazy("plugin_list")


class EnabledPluginView(CreateView):
    model = EnabledPlugin
    fields = ["enabled", "plugin", "organization"]
    template_name = "new_enable_disable_plugin.html"

    def form_invalid(self, form):
        return redirect(reverse("plugin_list"))

    def get_success_url(self, **kwargs):
        redirect_url = self.get_form().data.get("current_url")

        if redirect_url and url_has_allowed_host_and_scheme(redirect_url, allowed_hosts=None):
            return redirect_url

        return reverse_lazy("plugin_list")


class EnabledPluginUpdateView(UpdateView):
    model = EnabledPlugin
    fields = ["enabled", "plugin", "organization"]
    template_name = "new_enable_disable_plugin.html"

    def form_invalid(self, form):
        return redirect(reverse("plugin_list"))

    def get_success_url(self, **kwargs):
        redirect_url = self.get_form().data.get("current_url")

        if redirect_url and url_has_allowed_host_and_scheme(redirect_url, allowed_hosts=None):
            return redirect_url

        return reverse_lazy("plugin_list")


class PluginCoverImageView(View):
    """Get the cover image of a plugin."""

    def get(self, request, plugin_id: str, *args, **kwargs):
        try:
            plugin = get_local_repository().by_id(plugin_id)
            if (plugin.path / "cover.jpg").exists():
                file = FileResponse((settings.BASE_DIR / "katalogus" / "boefjes" / "cover.jpg").open("rb"))
            else:
                file = FileResponse((settings.BASE_DIR / "katalogus" / "boefjes" / "cover.jpg").open("rb"))
        except KeyError:
            file = FileResponse((settings.BASE_DIR / "katalogus" / "boefjes" / "cover.jpg").open("rb"))

        file.headers["Cache-Control"] = "max-age=604800"
        return file
