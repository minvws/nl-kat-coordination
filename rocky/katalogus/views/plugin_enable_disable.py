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
                self.request, messages.WARNING, _("Boefje '{boefje_id}' disabled.").format(boefje_id=self.plugin.id)
            )
            return HttpResponseRedirect(request.POST.get("current_url"))

        try:
            plugin_settings = self.katalogus_client.get_plugin_settings(self.plugin.id)
        except RequestException:
            messages.add_message(
                self.request,
                messages.ERROR,
                _("Failed fetching settings for boefje {boefje_id}. Is the Katalogus up?").format(
                    boefje_id=self.plugin.id
                ),
            )
            return redirect(
                reverse(
                    "plugin_detail",
                    kwargs={
                        "organization_code": self.organization.code,
                        "plugin_id": self.plugin.id,
                        "plugin_type": self.plugin.type,
                    },
                )
            )

        if not self.check_required_settings(plugin_settings):
            messages.add_message(
                self.request,
                messages.INFO,
                _("Before enabling, please set the required settings for boefje '{boefje_id}'.").format(
                    boefje_id=self.plugin.id
                ),
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

        self.katalogus_client.enable_boefje(self.plugin)
        messages.add_message(
            self.request, messages.SUCCESS, _("Boefje '{boefje_id}' enabled.").format(boefje_id=self.plugin.id)
        )

        return HttpResponseRedirect(request.POST.get("current_url"))
