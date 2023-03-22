import logging

from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView
from django_otp.decorators import otp_required
from requests import RequestException
from two_factor.views.utils import class_view_decorator

from katalogus.forms import PluginSchemaForm, PluginSettingAddEditForm
from katalogus.views.mixins import SinglePluginMixin


logger = logging.getLogger(__name__)


@class_view_decorator(otp_required)
class PluginSettingsAddView(PermissionRequiredMixin, SinglePluginMixin, FormView):
    """View to add a general setting for all plugins in KAT-alogus"""

    template_name = "plugin_settings_add.html"
    permission_required = "tools.can_scan_organization"

    def get_form(self, **kwargs):
        if not self.plugin_schema:
            return

        return PluginSchemaForm(self.plugin_schema, **self.get_form_kwargs())

    def form_valid(self, form):
        try:
            settings = self.katalogus_client.get_plugin_settings(self.plugin.id)
        except RequestException:
            messages.add_message(
                self.request, messages.ERROR, _("Failed getting settings for boefje {}").format(self.plugin.id)
            )
            return super().form_valid(form)

        for name, value in form.cleaned_data.items():
            if name in settings:
                self.add_error_notification(_("This setting already exists. Use the edit link."))
                break

            self.katalogus_client.add_plugin_setting(self.plugin.id, name, value)

        if "add-enable" in self.request.POST:
            self.katalogus_client.enable_boefje(self.plugin.id)
            messages.add_message(
                self.request, messages.SUCCESS, _("Boefje '{boefje_id}' enabled.").format(boefje_id=self.plugin.id)
            )

        self.add_success_notification()
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
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
                    "plugin_settings_add",
                    kwargs={
                        "organization_code": self.organization.code,
                        "plugin_type": self.plugin.type,
                        "plugin_id": self.plugin.id,
                    },
                ),
                "text": _("Add settings"),
            },
        ]
        context["plugin_id"] = self.plugin.id
        context["plugin_type"] = self.plugin.type
        context["plugin_name"] = self.plugin.name
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

    def add_success_notification(self):
        success_message = _("Setting successfully added for: ") + self.plugin.name
        messages.add_message(self.request, messages.SUCCESS, success_message)

    def add_error_notification(self, message):
        messages.add_message(self.request, messages.ERROR, message)


@class_view_decorator(otp_required)
class PluginSingleSettingAddView(PluginSettingsAddView):
    """View to add one specific setting."""

    template_name = "plugin_settings_add.html"
    permission_required = "tools.can_scan_organization"

    def dispatch(self, request, *args, **kwargs):
        if not self.plugin_schema:
            messages.add_message(
                self.request,
                messages.WARNING,
                _("No plugin schema found. You do not need to add settings to enable this plugin."),
            )
            return redirect(
                reverse(
                    "plugin_detail",
                    kwargs={
                        "organization_code": self.organization.code,
                        "plugin_type": self.plugin.type,
                        "plugin_id": self.plugin.id,
                    },
                )
            )

        if not self.is_setting(self.kwargs["setting_name"]):
            messages.add_message(self.request, messages.ERROR, _("Invalid setting name."))
            return redirect(
                reverse(
                    "plugin_detail",
                    kwargs={
                        "organization_code": self.organization.code,
                        "plugin_type": self.plugin.type,
                        "plugin_id": self.plugin.id,
                    },
                )
            )

        return super().dispatch(request, *args, **kwargs)

    def get_form(self, **kwargs):
        return PluginSettingAddEditForm(self.plugin_schema, self.kwargs["setting_name"], **self.get_form_kwargs())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["setting_name"] = self.kwargs["setting_name"]
        return context
