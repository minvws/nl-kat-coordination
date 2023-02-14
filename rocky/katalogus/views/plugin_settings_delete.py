from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from django_otp.decorators import otp_required
from two_factor.views.utils import class_view_decorator

from katalogus.views.mixins import KATalogusMixin


@class_view_decorator(otp_required)
class PluginSettingsDeleteView(PermissionRequiredMixin, KATalogusMixin, TemplateView):
    template_name = "plugin_settings_delete.html"
    permission_required = "tools.can_scan_organization"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.name = kwargs["name"]

    def post(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)

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
                    "plugin_settings_delete",
                    kwargs={
                        "organization_code": self.organization.code,
                        "plugin_type": self.plugin["type"],
                        "plugin_id": self.plugin_id,
                        "name": self.name,
                    },
                ),
                "text": _("Delete"),
            },
        ]
        context["name"] = self.name
        context["plugin_id"] = self.plugin_id
        context["plugin_type"] = self.plugin["type"]
        context["plugin_name"] = self.plugin["name"]
        context["cancel_url"] = self.get_success_url()
        return context

    def get_success_url(self):
        return reverse(
            "plugin_detail",
            kwargs={
                "organization_code": self.organization.code,
                "plugin_type": self.plugin["type"],
                "plugin_id": self.plugin_id,
            },
        )

    def delete(self, request, *args, **kwargs):
        self.katalogus_client.delete_plugin_setting(plugin_id=self.plugin_id, name=self.name)
        messages.add_message(
            request,
            messages.SUCCESS,
            _("Setting {} for plugin {} succesfully deleted.").format(self.name, self.plugin["name"]),
        )
        return HttpResponseRedirect(self.get_success_url())
