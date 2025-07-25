from django.conf import settings
from django.db.models import Q
from django.db.models.functions import Coalesce
from django.http import FileResponse
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from plugins.models import EnabledPlugin, Plugin


class PluginListView(ListView):
    template_name = "plugin_list.html"
    fields = ["enabled_plugins"]
    model = Plugin

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(Q(enabled_plugins__organization=self.get_organization()) | Q(enabled_plugins__isnull=True))
            .annotate(
                enabled=Coalesce("enabled_plugins__enabled", False), enabled_id=Coalesce("enabled_plugins__id", None)
            )
            .order_by("name")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"url": reverse("plugin_list"), "text": _("Plugins")}]

        return context

    def get_organization(self):  # TODO
        return None


class PluginDetailView(DetailView):
    template_name = "plugin.html"
    model = Plugin

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {"url": reverse("plugin_list"), "text": _("Plugins")},
            {"url": reverse("plugin_detail", kwargs={"pk": self.get_object().id}), "text": _("Plugin Detail")},
        ]

        return context


class EnabledPluginView(CreateView):
    model = EnabledPlugin
    fields = ["enabled", "plugin", "organization"]
    template_name = "new_enable_disable_plugin.html"
    success_url = reverse_lazy("plugin_list")


class EnabledPluginUpdateView(UpdateView):
    model = EnabledPlugin
    fields = ["enabled", "plugin", "organization"]
    template_name = "new_enable_disable_plugin.html"
    success_url = reverse_lazy("plugin_list")


class PluginCoverImageView(View):
    """Get the cover image of a plugin."""

    def get(self, request, plugin_id: str, *args, **kwargs):
        if (settings.BASE_DIR / "katalogus" / "boefjes" / plugin_id / "cover.jpg").exists():
            file = FileResponse((settings.BASE_DIR / "katalogus" / "boefjes" / plugin_id / "cover.jpg").open("rb"))
        else:
            file = FileResponse((settings.BASE_DIR / "katalogus" / "boefjes" / "cover.jpg").open("rb"))

        file.headers["Cache-Control"] = "max-age=604800"
        return file
