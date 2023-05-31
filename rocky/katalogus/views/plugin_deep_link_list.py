from account.mixins import OrganizationView
from django.views.generic import ListView

from katalogus.models import OrganizationPlugin


class PluginDeepLinkListView(OrganizationView, ListView):
    model = OrganizationPlugin
    template_name = "plugin_deep_link_list.html"
    context_object_name = "plugin_deep_link"
