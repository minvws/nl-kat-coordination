from typing import Any, List

from account.mixins import OrganizationView
from django.http import HttpRequest, HttpResponse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView
from tools.view_helpers import Breadcrumb, get_ooi_url

from katalogus.models import OrganizationPlugin
from rocky.views.mixins import SingleOOIMixin
from rocky.views.ooi_view import BaseOOIBreadcrumbs


class PluginDeepLinkDetailedListView(BaseOOIBreadcrumbs, SingleOOIMixin, ListView):
    """
    Listing deep links of a specific OOI related to an OOI-Type.
    Each OOI has a specific key/id to build the link, for example CVE codes in link.
    """

    model = OrganizationPlugin
    template_name = "plugin_deep_link_detailed_list.html"
    context_object_name = "plugin_deep_link"

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        ooi_id = self.request.GET.get("ooi_id", None)
        self.ooi = self.get_single_ooi(ooi_id)
        self.ooi_props = self.get_ooi_properties(self.ooi)
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
                    "link_text": self.replace_params_with_ooi_props(plugin.plugin.content),
                    "link": self.replace_params_with_ooi_props(plugin.plugin.link),
                }
            )
        return queryset

    def replace_params_with_ooi_props(self, target: str) -> str:
        for key, value in self.ooi_props.items():
            if value:
                target = target.replace("[" + key + "]", str(value))
        return target

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


class PluginDeepLinkListView(OrganizationView, ListView):
    """
    Listing all enabled deep link plugins of an organization in KAT-alogus.
    """

    model = OrganizationPlugin
    template_name = "plugin_deep_link_list.html"
    context_object_name = "deep_links"

    def get_queryset(self):
        return OrganizationPlugin.objects.filter(organization=self.organization)
