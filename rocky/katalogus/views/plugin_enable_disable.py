from logging import getLogger
from typing import Dict

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from requests import RequestException

from katalogus.views.mixins import SinglePluginView

logger = getLogger(__name__)


class PluginEnableDisableView(SinglePluginView):
    def check_required_settings(self, settings: Dict):
        if self.plugin_schema is None:
            return True

        return all([field in settings for field in self.plugin_schema["required"]])

    def post(self, request, *args, **kwargs):
        plugin_state = kwargs["plugin_state"]
        if plugin_state == "True":
            self.katalogus_client.disable_boefje(self.plugin)
            messages.add_message(
                self.request,
                messages.WARNING,
                _("{} '{}' disabled.").format(self.plugin.type.title(), self.plugin.name),
            )
            return HttpResponseRedirect(request.POST.get("current_url"))

        try:
            plugin_settings = self.katalogus_client.get_plugin_settings(self.plugin.id)
        except RequestException:
            messages.add_message(
                self.request,
                messages.ERROR,
                _("Failed fetching settings for {}. Is the Katalogus up?").format(self.plugin.name),
            )
            return redirect(
                reverse(
                    "boefje_detail",
                    kwargs={
                        "organization_code": self.organization.code,
                        "plugin_id": self.plugin.id,
                    },
                )
            )

        if not self.check_required_settings(plugin_settings):
            messages.add_message(
                self.request,
                messages.INFO,
                _("Before enabling, please set the required settings for '{}'.").format(self.plugin.name),
            )
            return redirect(
                reverse(
                    "plugin_settings_add",
                    kwargs={
                        "organization_code": self.organization.code,
                        "plugin_id": self.plugin.id,
                        "plugin_type": self.plugin.type,
                    },
                )
            )

        if self.plugin.can_scan(self.organization_member):
            self.katalogus_client.enable_boefje(self.plugin)
            messages.add_message(
                self.request,
                messages.SUCCESS,
                _("{} '{}' enabled.").format(self.plugin.type.title(), self.plugin.name),
            )
        else:
            member_clearance_level_text = (
                "Your clearance level is L{}. Contact your administrator to get a higher clearance level."
            ).format(self.organization_member.acknowledged_clearance_level)

            if (
                self.organization_member.trusted_clearance_level < 0
                or self.organization_member.acknowledged_clearance_level < 0
            ):
                member_clearance_level_text = _(
                    "Your clearance level is not set. Go to your profile page to see your clearance "
                    "or contact the administrator to set a clearance level."
                )

            messages.add_message(
                self.request,
                messages.ERROR,
                _("To enable {} you need at least a clearance level of L{}. " + member_clearance_level_text).format(
                    self.plugin.name.title(),
                    self.plugin.scan_level.value,
                ),
            )

        return HttpResponseRedirect(request.POST.get("current_url"))
