from logging import getLogger

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django_otp.decorators import otp_required
from two_factor.views.utils import class_view_decorator

from katalogus.views.mixins import SinglePluginMixin

logger = getLogger(__name__)


@class_view_decorator(otp_required)
class PluginEnableDisableView(SinglePluginMixin):
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def check_required_settings(self):
        if not self.plugin_schema:
            return True

        settings = self.katalogus_client.get_plugin_settings(self.plugin.id)

        return all([field in settings for field in self.plugin_schema["required"]])

    def post(self, request, *args, **kwargs):
        plugin_type = kwargs["plugin_type"]
        plugin_state = kwargs["plugin_state"]
        if plugin_state == "True":
            self.katalogus_client.disable_boefje(self.plugin.id)
            messages.add_message(
                self.request, messages.WARNING, _("Boefje '{boefje_id}' disabled.").format(boefje_id=self.plugin.id)
            )
        else:
            if self.check_required_settings():
                self.katalogus_client.enable_boefje(self.plugin.id)
                messages.add_message(
                    self.request, messages.SUCCESS, _("Boefje '{boefje_id}' enabled.").format(boefje_id=self.plugin.id)
                )
            else:
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
                            "plugin_type": plugin_type,
                        },
                    )
                )
        return HttpResponseRedirect(request.POST.get("current_url"))
