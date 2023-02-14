from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView
from django_otp.decorators import otp_required
from two_factor.views.utils import class_view_decorator

from katalogus.forms import PluginSchemaForm, PluginSettingAddEditForm
from katalogus.views.mixins import KATalogusMixin


@class_view_decorator(otp_required)
class PluginSettingsAddView(PermissionRequiredMixin, KATalogusMixin, FormView):
    """View to add a general setting for all plugins in KAT-alogus"""

    template_name = "plugin_settings_add.html"
    permission_required = "tools.can_scan_organization"

    def get_form(self):
        if self.plugin_schema:
            form = PluginSchemaForm(self.plugin_schema, **self.get_form_kwargs())
            return form

    def form_valid(self, form):
        for name, value in form.cleaned_data.items():
            if self.is_name_duplicate(name):
                self.add_error_notification(_("This setting already exists. Use the edit link."))
                break

            self.katalogus_client.add_plugin_setting(self.plugin_id, name, value)

        if "add-enable" in self.request.POST:
            self.katalogus_client.enable_boefje(self.plugin_id)
            messages.add_message(
                self.request, messages.SUCCESS, _("Boefje '{boefje_id}' enabled.").format(boefje_id=self.plugin_id)
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
                        "plugin_type": self.plugin["type"],
                        "plugin_id": self.plugin_id,
                    },
                ),
                "text": self.plugin["name"],
            },
            {
                "url": reverse(
                    "plugin_settings_add",
                    kwargs={
                        "organization_code": self.organization.code,
                        "plugin_type": self.plugin["type"],
                        "plugin_id": self.plugin_id,
                    },
                ),
                "text": _("Add settings"),
            },
        ]
        context["plugin_id"] = self.plugin_id
        context["plugin_type"] = self.plugin["type"]
        context["plugin_name"] = self.plugin["name"]
        return context

    def is_name_duplicate(self, name):
        setting = self.katalogus_client.get_plugin_setting(self.plugin_id, name=name)
        return "message" not in setting

    def get_success_url(self):
        return reverse(
            "plugin_detail",
            kwargs={
                "organization_code": self.organization.code,
                "plugin_type": self.plugin["type"],
                "plugin_id": self.plugin_id,
            },
        )

    def add_success_notification(self):
        success_message = _("Setting succesfully added for: ") + self.plugin["name"]
        messages.add_message(self.request, messages.SUCCESS, success_message)

    def add_error_notification(self, message):
        messages.add_message(self.request, messages.ERROR, message)


@class_view_decorator(otp_required)
class PluginSingleSettingAddView(PluginSettingsAddView):
    """View to add one specific setting."""

    template_name = "plugin_settings_add.html"
    permission_required = "tools.can_scan_organization"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.setting_name = kwargs["setting_name"]

    def get_form(self):
        if self.plugin_schema:
            form = PluginSettingAddEditForm(self.plugin_schema, self.setting_name, **self.get_form_kwargs())
            return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["setting_name"] = self.setting_name
        return context
