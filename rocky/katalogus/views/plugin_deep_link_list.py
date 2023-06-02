from typing import Any, List

from django.http import HttpRequest, HttpResponse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView
from tools.view_helpers import Breadcrumb, get_ooi_url

from katalogus.models import OrganizationPlugin
from rocky.views.mixins import OctopoesView
from rocky.views.ooi_view import BaseOOIBreadcrumbs


def replace_link_id_param(link: str, key: str) -> str:
    return link.split("[")[0] + key


class PluginDeepLinkListView(BaseOOIBreadcrumbs, OctopoesView, ListView):
    model = OrganizationPlugin
    template_name = "plugin_deep_link_list.html"
    context_object_name = "plugin_deep_link"

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        ooi_id = self.request.GET.get("ooi_id", None)
        self.ooi = self.get_single_ooi(ooi_id)
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = []

        plugins = OrganizationPlugin.objects.filter(
            organization=self.organization, plugin__ooi_type=self.ooi.ooi_type, enabled=True
        )
        for plugin in plugins:
            queryset.append(
                {
                    "name": plugin.plugin.name,
                    "link_text": replace_link_id_param(plugin.plugin.content, self.ooi.natural_key),
                    "link": replace_link_id_param(plugin.plugin.link, self.ooi.natural_key),
                }
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ooi"] = self.ooi
        return context

    def build_breadcrumbs(self) -> List[Breadcrumb]:
        breadcrumbs = super().build_breadcrumbs()
        breadcrumbs.append(
            {
                "url": get_ooi_url("ooi_sources", self.ooi.primary_key, self.organization.code),
                "text": _("Deep Links"),
            }
        )
        return breadcrumbs
