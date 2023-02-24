from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.urls import reverse
from django.urls.base import reverse_lazy
from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.views.generic import ListView, FormView, TemplateView
from django_otp.decorators import otp_required
from two_factor.views.utils import class_view_decorator
from account.forms.organization import OrganizationListForm
from account.mixins import OrganizationView
from katalogus.client import get_katalogus
from tools.models import Organization, OrganizationMember


@class_view_decorator(otp_required)
class ConfirmCloneSettingsView(OrganizationView, UserPassesTestMixin, TemplateView):
    template_name = "confirmation_clone_settings.html"

    def test_func(self):
        to_organization = Organization.objects.get(code=self.kwargs["to_organization"])

        return OrganizationMember.objects.filter(user=self.request.user, organization=to_organization).exists()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["to_organization"] = Organization.objects.get(code=kwargs["to_organization"])

        return context

    def post(self, request, *args, **kwargs):
        to_organization = Organization.objects.get(code=kwargs["to_organization"])
        get_katalogus(self.organization.code).clone_all_configuration_to_organization(to_organization.code)
        messages.add_message(
            self.request,
            messages.SUCCESS,
            _("Settings from %s to %s successfully cloned.")
            % (
                to_organization.name,
                self.organization.name,
            ),
        )
        return HttpResponseRedirect(
            reverse(
                "katalogus_settings",
                kwargs={"organization_code": self.organization.code},
            )
        )


@class_view_decorator(otp_required)
class KATalogusSettingsListView(PermissionRequiredMixin, OrganizationView, FormView, ListView):
    """View that gives an overview of all plugins settings"""

    template_name = "katalogus_settings.html"
    paginate_by = 10
    permission_required = "tools.can_scan_organization"
    plugin_type = "boefjes"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {
                "url": reverse("katalogus", kwargs={"organization_code": self.organization.code}),
                "text": _("KAT-alogus"),
            },
            {
                "url": reverse("katalogus_settings", kwargs={"organization_code": self.organization.code}),
                "text": _("Settings"),
            },
        ]
        context["plugin_type"] = self.plugin_type
        return context

    def get_queryset(self):
        all_plugins_settings = []
        katalogus_client = get_katalogus(self.organization.code)
        boefjes = katalogus_client.get_boefjes()
        for boefje in boefjes:
            plugin_settings = {}
            plugin_setting = katalogus_client.get_plugin_settings(boefje.id)
            if plugin_setting:
                plugin_settings["plugin_id"] = boefje.id
                plugin_settings["plugin_name"] = boefje.name
                for key, value in plugin_setting.items():
                    plugin_settings["name"] = key
                    plugin_settings["value"] = value
                all_plugins_settings.append(plugin_settings)
        return all_plugins_settings

    def get_form(self, form_class=None):
        return OrganizationListForm(
            user=self.request.user, exclude_organization=self.organization, **self.get_form_kwargs()
        )

    def form_valid(self, form):
        return HttpResponseRedirect(self.get_success_url(to_organization=form.cleaned_data["organization"]))

    def get_success_url(self, **kwargs):
        return reverse_lazy(
            "confirm_clone_settings",
            kwargs={"organization_code": self.organization.code, "to_organization": kwargs["to_organization"]},
        )
