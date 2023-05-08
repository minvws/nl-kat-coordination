from account.mixins import OrganizationPermissionRequiredMixin
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from django_otp.decorators import otp_required
from requests import RequestException
from two_factor.views.utils import class_view_decorator

from katalogus.views.mixins import SingleSettingView


@class_view_decorator(otp_required)
class PluginSettingsDeleteView(OrganizationPermissionRequiredMixin, SingleSettingView, TemplateView):
    template_name = "plugin_settings_delete.html"
    permission_required = "tools.can_scan_organization"

    def post(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)

    def get_context_data(self, setting_name: str, **kwargs):
        context = super().get_context_data(setting_name=setting_name, **kwargs)

        context["breadcrumbs"] = [
            {
                "url": reverse("katalogus", kwargs={"organization_code": self.organization.code}),
                "text": _("KAT-alogus"),
            },
            {
                "url": reverse(
                    "plugin_detail",
                    kwargs={
                        "organization_code": self.organization.code,
                        "plugin_type": self.plugin.type,
                        "plugin_id": self.plugin.id,
                    },
                ),
                "text": self.plugin.name,
            },
            {
                "url": reverse(
                    "plugin_settings_delete",
                    kwargs={
                        "organization_code": self.organization.code,
                        "plugin_type": self.plugin.type,
                        "plugin_id": self.plugin.id,
                        "setting_name": setting_name,
                    },
                ),
                "text": _("Delete"),
            },
        ]
        context["setting_name"] = setting_name
        context["plugin_id"] = self.plugin.id
        context["plugin_type"] = self.plugin.type
        context["plugin_name"] = self.plugin.name
        context["cancel_url"] = self.get_success_url()
        return context

    def get_success_url(self):
        return reverse(
            "plugin_detail",
            kwargs={
                "organization_code": self.organization.code,
                "plugin_type": self.plugin.type,
                "plugin_id": self.plugin.id,
            },
        )

    def delete(self, request, setting_name: str, *args, **kwargs):
        try:
            self.katalogus_client.delete_plugin_setting(plugin_id=self.plugin.id, name=setting_name)
            messages.add_message(
                request,
                messages.SUCCESS,
                _("Setting {} for plugin {} successfully deleted.").format(setting_name, self.plugin.name),
            )
        except RequestException:
            messages.add_message(
                request,
                messages.ERROR,
                _("Failed deleting Setting {} for plugin {}. Check the Katalogus logs for more info.").format(
                    setting_name, self.plugin.name
                ),
            )
            return HttpResponseRedirect(self.get_success_url())

        return HttpResponseRedirect(self.get_success_url())
