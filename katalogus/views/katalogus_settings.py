from django.contrib.auth.mixins import PermissionRequiredMixin
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView
from django_otp.decorators import otp_required
from two_factor.views.utils import class_view_decorator

from account.mixins import OrganizationView
from katalogus.client import get_katalogus


@class_view_decorator(otp_required)
class KATalogusSettingsListView(PermissionRequiredMixin, OrganizationView, ListView):
    """View that gives an overview of all plugins settings"""

    template_name = "katalogus_settings.html"
    paginate_by = 10
    permission_required = "tools.can_scan_organization"
    plugin_type = "boefjes"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {
                "url": reverse("katalogus", kwargs={"organization_code": self.organization.code}),
                "text": _("KAT-alogus"),
            },
            {
                "url": reverse("katalogus_settings", kwargs={"organization_code": self.organization.code}),
                "text": _("Settings"),
            },
        ]
        context["plugin_type"] = self.plugin_type
        return context

    def get_queryset(self):
        all_plugins_settings = []
        katalogus_client = get_katalogus(self.organization.code)
        boefjes = katalogus_client.get_boefjes()
        for boefje in boefjes:
            plugin_settings = {}
            plugin_setting = katalogus_client.get_plugin_settings(boefje.id)
            if plugin_setting:
                plugin_settings["plugin_id"] = boefje.id
                plugin_settings["plugin_name"] = boefje.name
                for key, value in plugin_setting.items():
                    plugin_settings["name"] = key
                    plugin_settings["value"] = value
                all_plugins_settings.append(plugin_settings)
        return all_plugins_settings
