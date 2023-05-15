from account.mixins import OrganizationPermissionRequiredMixin
from django.contrib import messages
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView
from django_otp.decorators import otp_required
from requests import RequestException
from two_factor.views.utils import class_view_decorator

from katalogus.forms import PluginSettingAddEditForm
from katalogus.views.mixins import SingleSettingView


@class_view_decorator(otp_required)
class PluginSettingsUpdateView(OrganizationPermissionRequiredMixin, SingleSettingView, FormView):
    """View to update/edit a plugin setting for all plugins in KAT-alogus"""

    template_name = "plugin_settings_edit.html"
    permission_required = "tools.can_scan_organization"

    def get_form(self, **kwargs):
        settings_value = self.katalogus_client.get_plugin_settings(self.plugin.id).get(self.setting_name)

        if settings_value is None:
            return

        return PluginSettingAddEditForm(self.plugin_schema, self.setting_name, settings_value, **self.get_form_kwargs())

    def get_success_url(self):
        return reverse(
            "plugin_detail",
            kwargs={
                "organization_code": self.organization.code,
                "plugin_type": self.plugin.type,
                "plugin_id": self.plugin.id,
            },
        )

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
                    "plugin_settings_edit",
                    kwargs={
                        "organization_code": self.organization.code,
                        "plugin_type": self.plugin.type,
                        "plugin_id": self.plugin.id,
                        "setting_name": self.setting_name,
                    },
                ),
                "text": _("Edit"),
            },
        ]
        context["setting_name"] = self.setting_name
        context["plugin_id"] = self.plugin.id
        context["plugin_type"] = self.plugin.type
        context["plugin_name"] = self.plugin.name
        return context

    def form_valid(self, form):
        try:
            self.katalogus_client.update_plugin_setting(
                plugin_id=self.plugin.id, name=self.setting_name, value=form.cleaned_data[self.setting_name]
            )
            messages.add_message(self.request, messages.SUCCESS, _("Setting successfully updated."))
        except RequestException:
            messages.add_message(self.request, messages.ERROR, _("Failed updating setting."))

        return super().form_valid(form)
