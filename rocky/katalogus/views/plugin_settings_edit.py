from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView
from django_otp.decorators import otp_required
from two_factor.views.utils import class_view_decorator

from katalogus.forms import PluginSettingAddEditForm
from katalogus.views.mixins import KATalogusMixin


@class_view_decorator(otp_required)
class PluginSettingsUpdateView(PermissionRequiredMixin, KATalogusMixin, FormView):
    """View to update/edit a plugin setting for all plugins in KAT-alogus"""

    template_name = "plugin_settings_edit.html"
    permission_required = "tools.can_scan_organization"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.setting_name = kwargs["setting_name"]
        self.setting_value = self.katalogus_client.get_plugin_setting(self.plugin_id, name=self.setting_name)
        self.check_key_already_exists(request)

    def get_form(self):
        if self.plugin_schema:
            form = PluginSettingAddEditForm(
                self.plugin_schema, self.setting_name, self.setting_value, **self.get_form_kwargs()
            )
            return form

    def check_key_already_exists(self, request):
        if "message" in self.setting_value:
            messages.add_message(
                request,
                messages.ERROR,
                _("The setting you are trying to edit does not exist."),
            )
            return HttpResponseRedirect(
                reverse(
                    "plugin_detail",
                    kwargs={
                        "organization_code": self.organization.code,
                        "plugin_type": self.plugin["type"],
                        "plugin_id": self.plugin_id,
                    },
                )
            )

    def get_success_url(self):
        return reverse(
            "plugin_detail",
            kwargs={
                "organization_code": self.organization.code,
                "plugin_type": self.plugin["type"],
                "plugin_id": self.plugin_id,
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
                "text": _("Edit"),
            },
        ]
        context["setting_name"] = self.setting_name
        context["plugin_id"] = self.plugin_id
        context["plugin_type"] = self.plugin["type"]
        context["plugin_name"] = self.plugin["name"]
        return context

    def form_valid(self, form):
        value = form.cleaned_data[self.setting_name]
        self.katalogus_client.update_plugin_setting(plugin_id=self.plugin_id, name=self.setting_name, value=value)
        messages.add_message(self.request, messages.SUCCESS, _("Setting succesfully updated."))
        return super().form_valid(form)
