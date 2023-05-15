import logging

from account.mixins import OrganizationPermissionRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView
from django_otp.decorators import otp_required
from requests import RequestException
from two_factor.views.utils import class_view_decorator

from katalogus.forms import PluginSchemaForm, PluginSettingAddEditForm
from katalogus.views.mixins import SinglePluginView, SingleSettingView

logger = logging.getLogger(__name__)


@class_view_decorator(otp_required)
class PluginSettingsAddView(OrganizationPermissionRequiredMixin, SinglePluginView, FormView):
    """View to add a general setting for all plugins in KAT-alogus"""

    template_name = "plugin_settings_add.html"
    permission_required = "tools.can_scan_organization"

    def get_form(self, **kwargs):
        if self.plugin_schema is None:
            return None

        return PluginSchemaForm(self.plugin_schema, **self.get_form_kwargs())

    def form_valid(self, form):
        if self.plugin_schema is None:
            messages.add_message(
                self.request,
                messages.WARNING,
                _("Trying to add settings to boefje without schema").format(self.plugin.id),
            )
            return redirect(self.get_success_url())

        try:
            settings = self.katalogus_client.get_plugin_settings(self.plugin.id)
        except RequestException:
            messages.add_message(
                self.request, messages.ERROR, _("Failed getting settings for boefje {}").format(self.plugin.id)
            )
            return redirect(self.get_success_url())

        for name, value in form.cleaned_data.items():
            if name in settings:
                self.add_error_notification(_("Setting {} already exists. Use the edit link.").format(name))
                return redirect(self.get_success_url())

            try:
                self.katalogus_client.add_plugin_setting(self.plugin.id, name, value)
                messages.add_message(
                    self.request, messages.SUCCESS, _("Setting {} added for {} ").format(name, self.plugin.name)
                )
            except RequestException:
                messages.add_message(self.request, messages.ERROR, _("Failed adding setting {}").format(name))
                return redirect(self.get_success_url())

        if "add-enable" in self.request.POST:
            try:
                self.katalogus_client.enable_boefje(self.plugin)
            except RequestException:
                messages.add_message(self.request, messages.ERROR, _("Enabling {} failed").format(self.plugin.id))
                return redirect(self.get_success_url())

            messages.add_message(self.request, messages.SUCCESS, _("Boefje '{}' enabled.").format(self.plugin.id))

        return redirect(self.get_success_url())

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

    def add_error_notification(self, message):
        messages.add_message(self.request, messages.ERROR, message)


@class_view_decorator(otp_required)
class PluginSingleSettingAddView(PluginSettingsAddView, SingleSettingView):
    """View to add one specific setting."""

    template_name = "plugin_settings_add.html"
    permission_required = "tools.can_scan_organization"

    def get_form(self, **kwargs):
        return PluginSettingAddEditForm(self.plugin_schema, self.setting_name, **self.get_form_kwargs())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["setting_name"] = self.setting_name
        return context
