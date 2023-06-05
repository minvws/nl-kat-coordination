from account.mixins import OrganizationView
from django.views.generic import DetailView

from katalogus.models import PluginDeepLink


class PluginDeepLinkDetailView(OrganizationView, DetailView):
    model = PluginDeepLink
    template_name = "plugin_deep_link_detail.html"
