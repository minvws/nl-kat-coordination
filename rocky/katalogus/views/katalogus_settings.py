from account.forms.organization import OrganizationListForm
from account.mixins import OrganizationView
from account.models import KATUser
from django.contrib import messages
from account.mixins import RockyPermissionRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.urls.base import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView, ListView, TemplateView
from django_otp.decorators import otp_required
from requests import RequestException
from tools.models import Organization
from two_factor.views.utils import class_view_decorator

from katalogus.client import get_katalogus


@class_view_decorator(otp_required)
class ConfirmCloneSettingsView(OrganizationView, UserPassesTestMixin, TemplateView):
    template_name = "confirmation_clone_settings.html"

    def test_func(self):
        user: KATUser = self.request.user
        return self.kwargs["to_organization"] in {org.code for org in user.organizations}

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
                self.organization.name,
                to_organization.name,
            ),
        )
        return HttpResponseRedirect(
            reverse(
                "katalogus_settings",
                kwargs={"organization_code": self.organization.code},
            )
        )


@class_view_decorator(otp_required)
class KATalogusSettingsListView(RockyPermissionRequiredMixin, OrganizationView, FormView, ListView):
    """View that gives an overview of all plugins settings"""

    template_name = "katalogus_settings.html"
    paginate_by = 10
    permission_required = "can_scan_organization"
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

            try:
                plugin_setting = katalogus_client.get_plugin_settings(boefje.id)
            except RequestException:
                messages.add_message(
                    self.request, messages.ERROR, _("Failed getting settings for boefje {}").format(self.plugin.id)
                )
                continue

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
