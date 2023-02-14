from logging import getLogger

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django_otp.decorators import otp_required
from two_factor.views.utils import class_view_decorator

from account.mixins import OrganizationView
from katalogus.client import get_katalogus

logger = getLogger(__name__)


@class_view_decorator(otp_required)
class PluginEnableDisableView(OrganizationView):
    def dispatch(self, request, *args, **kwargs):
        self.katalogus_client = get_katalogus(self.organization.code)
        return super().dispatch(request, *args, **kwargs)

    def check_required_settings(self, plugin_id):
        plugin_schema = self.katalogus_client.get_plugin_schema(plugin_id)
        if plugin_schema:
            required_fields = plugin_schema["required"]
            for field in required_fields:
                if "message" in self.katalogus_client.get_plugin_setting(plugin_id, field):
                    return False
        return True

    def post(self, request, *args, **kwargs):
        plugin_id = kwargs["plugin_id"]
        plugin_type = kwargs["plugin_type"]
        plugin_state = kwargs["plugin_state"]
        if plugin_state == "True":
            self.katalogus_client.disable_boefje(plugin_id)
            messages.add_message(
                self.request, messages.WARNING, _("Boefje '{boefje_id}' disabled.").format(boefje_id=plugin_id)
            )
        else:
            if self.check_required_settings(plugin_id):
                self.katalogus_client.enable_boefje(plugin_id)
                messages.add_message(
                    self.request, messages.SUCCESS, _("Boefje '{boefje_id}' enabled.").format(boefje_id=plugin_id)
                )
            else:
                messages.add_message(
                    self.request,
                    messages.INFO,
                    _("Before enabling, please set the required settings for boefje '{boefje_id}'.").format(
                        boefje_id=plugin_id
                    ),
                )
                return redirect(
                    reverse(
                        "plugin_settings_add",
                        kwargs={
                            "organization_code": self.organization.code,
                            "plugin_id": plugin_id,
                            "plugin_type": plugin_type,
                        },
                    )
                )
        return HttpResponseRedirect(request.POST.get("current_url"))
