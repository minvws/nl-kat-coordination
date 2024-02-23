from typing import Any

from account.forms import MemberRegistrationForm, OnboardingOrganizationUpdateForm, OrganizationForm
from account.mixins import (
    OrganizationPermissionRequiredMixin,
    OrganizationView,
)
from account.views import OOIClearanceMixin
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import BadRequest
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.urls.base import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView, FormView, UpdateView
from katalogus.client import get_katalogus
from reports.report_types.dns_report.report import DNSReport
from reports.views.base import get_selection
from requests import HTTPError
from tools.models import GROUP_ADMIN, GROUP_CLIENT, GROUP_REDTEAM, Organization, OrganizationMember
from tools.ooi_helpers import (
    get_or_create_ooi,
)
from tools.view_helpers import Breadcrumb, get_ooi_url

from octopoes.models.ooi.network import Network
from octopoes.models.ooi.web import URL
from onboarding.forms import OnboardingCreateObjectURLForm, OnboardingSetClearanceLevelForm
from onboarding.view_helpers import (
    DNS_REPORT_LEAST_CLEARANCE_LEVEL,
    ONBOARDING_PERMISSIONS,
    KatIntroductionAdminStepsMixin,
    KatIntroductionRegistrationStepsMixin,
    KatIntroductionStepsMixin,
    OnboardingBreadcrumbsMixin,
    RegistrationBreadcrumbsMixin,
)
from rocky.exceptions import (
    RockyError,
)
from rocky.messaging import clearance_level_warning_dns_report
from rocky.views.indemnification_add import IndemnificationAddView
from rocky.views.ooi_view import SingleOOITreeMixin

User = get_user_model()


class OnboardingStart(OrganizationView):
    def get(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return redirect("step_introduction_registration")
        if self.organization_member.has_perms(ONBOARDING_PERMISSIONS):
            return redirect("step_introduction", kwargs={"organization_code": self.organization.code})
        return redirect("crisis_room")


# REDTEAMER FLOW


class OnboardingIntroductionView(
    OrganizationPermissionRequiredMixin,
    KatIntroductionStepsMixin,
    OrganizationView,
    TemplateView,
):
    """
    1. Start the onboarding wizard. What is OpenKAT and what it does.
    """

    template_name = "step_1_introduction.html"
    current_step = 1
    permission_required = "tools.can_scan_organization"


class OnboardingChooseReportInfoView(
    OrganizationPermissionRequiredMixin,
    KatIntroductionStepsMixin,
    OrganizationView,
    TemplateView,
):
    """
    2. Introduction into reporting. All the necessities to generate a report.
    """

    template_name = "step_2a_choose_report_info.html"
    current_step = 2
    permission_required = "tools.can_scan_organization"


class OnboardingChooseReportTypeView(
    OrganizationPermissionRequiredMixin,
    KatIntroductionStepsMixin,
    OrganizationView,
    TemplateView,
):
    """
    3. Choose a report type. Gives the user a choice of many report types. Ex. DNS report
    """

    template_name = "step_2b_choose_report_type.html"
    current_step = 2
    permission_required = "tools.can_scan_organization"


class OnboardingSetupScanOOIInfoView(
    OrganizationPermissionRequiredMixin,
    KatIntroductionStepsMixin,
    OrganizationView,
    TemplateView,
):
    """
    4. Explanation that an object is needed to make scans.
    """

    template_name = "step_3a_setup_scan_ooi_info.html"
    current_step = 3
    permission_required = "tools.can_scan_organization"


class OnboardingSetupScanOOIAddView(
    OrganizationPermissionRequiredMixin,
    KatIntroductionStepsMixin,
    SingleOOITreeMixin,
    FormView,
):
    """
    5. The user will create the object (URL object for example). Shows a form to create object.
    """

    template_name = "step_3b_setup_scan_ooi_add.html"
    current_step = 3
    permission_required = "tools.can_scan_organization"
    form_class = OnboardingCreateObjectURLForm

    def form_valid(self, form):
        cleaned_url = form.cleaned_data["url"]
        url = URL(network=Network(name="internet").reference, raw=cleaned_url)
        ooi, _ = get_or_create_ooi(self.octopoes_api_connector, self.bytes_client, url)
        selection = {"ooi": ooi.primary_key, "report_type": self.request.GET.get("report_type", "")}
        return redirect(
            reverse("step_clearance_level_introduction", kwargs={"organization_code": self.organization.code})
            + get_selection(self.request, selection)
        )

    def build_breadcrumbs(self) -> list[Breadcrumb]:
        return super().build_breadcrumbs() + [
            {
                "url": reverse("ooi_add_type_select", kwargs={"organization_code": self.organization.code})
                + get_selection(self.request),
                "text": _("Creating an object"),
            },
        ]

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["type"] = ""
        return context


class OnboardingClearanceLevelIntroductionView(
    OrganizationPermissionRequiredMixin,
    KatIntroductionStepsMixin,
    OnboardingBreadcrumbsMixin,
    OrganizationView,
    TemplateView,
):
    """
    6. Explanation what clearance levels mean.
    """

    template_name = "step_3d_clearance_level_introduction.html"
    permission_required = "tools.can_set_clearance_level"
    current_step = 3

    def get_boefjes_tiles(self) -> list[dict[str, Any]]:
        tiles = [
            {
                "id": "dns_zone",
                "type": "boefje",
                "scan_level": "l1",
                "name": "DNS-Zone",
                "description": _("Fetch the parent DNS zone of a hostname"),
                "enabled": False,
            },
            {
                "id": "fierce",
                "type": "boefje",
                "scan_level": "l3",
                "name": "Fierce",
                "description": _("Finds subdomains by brute force"),
                "enabled": False,
            },
        ]
        return tiles

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ooi"] = self.request.GET.get("ooi", None)
        context["boefjes"] = self.get_boefjes_tiles()
        return context


class OnboardingAcknowledgeClearanceLevelView(
    OrganizationPermissionRequiredMixin,
    KatIntroductionStepsMixin,
    OnboardingBreadcrumbsMixin,
    OOIClearanceMixin,
    OrganizationView,
    TemplateView,
):
    """
    7. Explains the user that before setting a clearance level, they must have a permissiom to do so.
    Here they acknowledge the clearance level assigned by their administrator.
    """

    template_name = "step_3e_trusted_acknowledge_clearance_level.html"
    permission_required = "tools.can_set_clearance_level"
    current_step = 3

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ooi"] = self.request.GET.get("ooi_id", None)
        context["dns_report_least_clearance_level"] = DNS_REPORT_LEAST_CLEARANCE_LEVEL
        return context


class OnboardingSetClearanceLevelView(
    OrganizationPermissionRequiredMixin,
    KatIntroductionStepsMixin,
    OnboardingBreadcrumbsMixin,
    SingleOOITreeMixin,
    TemplateView,
):
    """
    8. Set the actual clearance level on the object created before.
    """

    template_name = "step_3f_set_clearance_level.html"
    permission_required = "tools.can_set_clearance_level"
    current_step = 3

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        ooi_id = self.request.GET.get("ooi_id")
        ooi = self.get_ooi(ooi_id)
        level = DNS_REPORT_LEAST_CLEARANCE_LEVEL
        if not self.can_raise_clearance_level(ooi, level):
            return self.get(request, *args, **kwargs)
        return redirect(get_ooi_url("step_setup_scan_select_plugins", ooi_id, self.organization.code))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = OnboardingSetClearanceLevelForm(initial={"level": DNS_REPORT_LEAST_CLEARANCE_LEVEL})
        return context


class OnboardingSetupScanSelectPluginsView(
    OrganizationPermissionRequiredMixin,
    KatIntroductionStepsMixin,
    TemplateView,
):
    """
    9. Shows the user all required and optional plugins to select from. Required plugins are mandatory to continue.
    """

    template_name = "step_3g_setup_scan_select_plugins.html"
    current_step = 3
    plugins: dict[str, list[str]] = DNSReport.plugins
    permission_required = "tools.can_enable_disable_boefje"

    def get_plugins(self):
        plugins = {}
        for required_optional, plugin_ids in self.plugins.items():
            plugins[required_optional] = [
                get_katalogus(self.organization.code).get_plugin(plugin_id)
                for plugin_id in plugin_ids
                if get_katalogus(self.organization.code).get_plugin(plugin_id).scan_level
                <= DNS_REPORT_LEAST_CLEARANCE_LEVEL
            ]
        return plugins

    def post(self, request, *args, **kwargs):
        if "ooi_id" not in request.GET:
            raise BadRequest("No OOI ID provided")

        ooi_id = request.GET["ooi_id"]
        selected_plugins = request.POST.getlist("selected_plugins", [])

        if not selected_plugins:
            messages.error(request, _("Please select a plugin to proceed."))
            return self.get(request, *args, **kwargs)
        for plugin_id in self.plugins["required"]:
            if plugin_id not in selected_plugins:
                messages.error(request, _("Please select all required plugins to proceed."))
                return self.get(request, *args, **kwargs)
        for selected_plugin in selected_plugins:
            try:
                get_katalogus(self.organization.code).enable_boefje_by_id(selected_plugin)
            except HTTPError:
                messages.error(
                    request,
                    _("An error occurred while enabling {}. The plugin is not available.").format(selected_plugin),
                )
                return self.get(request, *args, **kwargs)

        messages.success(request, _("Plugins successfully enabled."))
        request.session["selected_boefjes"] = selected_plugins
        return redirect(get_ooi_url("step_setup_scan_ooi_detail", ooi_id, self.organization.code))

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["plugins"] = self.get_plugins()
        return context


class OnboardingSetupScanOOIDetailView(
    OrganizationPermissionRequiredMixin,
    SingleOOITreeMixin,
    KatIntroductionStepsMixin,
    OnboardingBreadcrumbsMixin,
    TemplateView,
):
    """
    9. Shows the user object information, more in depth info about the object.
    """

    template_name = "step_3c_setup_scan_ooi_detail.html"
    current_step = 3
    permission_required = "tools.can_scan_organization"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ooi"] = self.get_ooi(self.request.GET.get("ooi_id"))
        return context


class OnboardingReportView(
    OrganizationPermissionRequiredMixin,
    KatIntroductionStepsMixin,
    OrganizationView,
    TemplateView,
):
    """
    10. The user already started the scan and is now waiting till scans are finished to generate the report.
    Onboarding finished and member onboarded, next step will be the actual report.
    """

    template_name = "step_4_report.html"
    current_step = 4
    permission_required = "tools.can_scan_organization"

    def post(self, request, *args, **kwargs):
        if "ooi_id" not in request.GET:
            raise BadRequest("No OOI ID provided")
        ooi_id = request.GET["ooi_id"]

        self.set_member_onboarded()
        return redirect(get_ooi_url("dns_report", ooi_id, self.organization.code))

    def set_member_onboarded(self):
        member = OrganizationMember.objects.get(user=self.request.user, organization=self.organization)
        member.onboarded = True
        member.status = OrganizationMember.STATUSES.ACTIVE
        member.save()


# account flow


class OnboardingIntroductionRegistrationView(
    PermissionRequiredMixin, KatIntroductionRegistrationStepsMixin, TemplateView
):
    """
    Step: 1 - Registration introduction
    """

    template_name = "account/step_1_registration_intro.html"
    current_step = 1
    permission_required = "tools.add_organizationmember"


class OnboardingOrganizationSetupView(
    PermissionRequiredMixin,
    KatIntroductionRegistrationStepsMixin,
    CreateView,
):
    """
    Step 2: Create a new organization
    """

    model = Organization
    template_name = "account/step_2a_organization_setup.html"
    form_class = OrganizationForm
    current_step = 2
    permission_required = "tools.add_organization"

    def get(self, request, *args, **kwargs):
        members = OrganizationMember.objects.filter(user=self.request.user)
        if members:
            return redirect(
                reverse("step_organization_update", kwargs={"organization_code": members.first().organization.code})
            )
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except RockyError as e:
            messages.add_message(request, messages.ERROR, str(e))

        return self.get(request, *args, **kwargs)

    def get_success_url(self) -> str:
        self.create_first_member(self.object)
        return reverse_lazy("step_indemnification_setup", kwargs={"organization_code": self.object.code})

    def form_valid(self, form):
        org_name = form.cleaned_data["name"]
        result = super().form_valid(form)
        self.add_success_notification(org_name)
        return result

    def create_first_member(self, organization):
        member = OrganizationMember.objects.create(
            user=self.request.user,
            organization=organization,
        )
        if member.user.is_superuser:
            member.trusted_clearance_level = 4
            member.acknowledged_clearance_level = 4
            member.save()

    def add_success_notification(self, org_name):
        success_message = _("{org_name} successfully created.").format(org_name=org_name)
        messages.add_message(self.request, messages.SUCCESS, success_message)


class OnboardingOrganizationUpdateView(
    OrganizationPermissionRequiredMixin,
    KatIntroductionAdminStepsMixin,
    OrganizationView,
    UpdateView,
):
    """
    Step 2: Update an existing organization (only name not code)
    """

    model = Organization
    template_name = "account/step_2a_organization_update.html"
    form_class = OnboardingOrganizationUpdateForm
    current_step = 2
    permission_required = "tools.change_organization"

    def get_object(self, queryset=None):
        return self.organization

    def get_success_url(self) -> str:
        return reverse_lazy("step_indemnification_setup", kwargs={"organization_code": self.organization.code})

    def form_valid(self, form):
        org_name = form.cleaned_data["name"]
        self.add_success_notification(org_name)
        return super().form_valid(form)

    def add_success_notification(self, org_name):
        success_message = _("{org_name} successfully updated.").format(org_name=org_name)
        messages.add_message(self.request, messages.SUCCESS, success_message)


class OnboardingIndemnificationSetupView(
    KatIntroductionAdminStepsMixin,
    IndemnificationAddView,
):
    """
    Step 3: Agree to idemnification to scan oois
    """

    current_step = 3
    template_name = "account/step_2b_indemnification_setup.html"

    def get_success_url(self) -> str:
        return reverse_lazy("step_account_setup_intro", kwargs={"organization_code": self.organization.code})


class OnboardingAccountSetupIntroView(
    OrganizationPermissionRequiredMixin, KatIntroductionAdminStepsMixin, OrganizationView, TemplateView
):
    """
    Step 4: Split flow to or continue with single account or continue to multiple account creation
    """

    template_name = "account/step_2c_account_setup_intro.html"
    current_step = 4
    permission_required = "tools.add_organizationmember"


class OnboardingAccountCreationMixin(
    OrganizationPermissionRequiredMixin, KatIntroductionAdminStepsMixin, OrganizationView, FormView
):
    account_type: str | None = None
    permission_required = "tools.add_organizationmember"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.organization
        kwargs["account_type"] = self.account_type
        return kwargs


# Account setup for multiple user accounts: redteam, admins, clients


class OnboardingChooseUserTypeView(
    OrganizationPermissionRequiredMixin, KatIntroductionAdminStepsMixin, OrganizationView, TemplateView
):
    """
    Step 1: Introduction about how to create multiple user accounts
    """

    current_step = 4
    template_name = "account/step_3_account_user_type.html"
    permission_required = "tools.add_organizationmember"


class OnboardingAccountSetupAdminView(
    RegistrationBreadcrumbsMixin,
    OnboardingAccountCreationMixin,
):
    """
    Step 1: Create an admin account with admin rights
    """

    template_name = "account/step_4_account_setup_admin.html"
    form_class = MemberRegistrationForm
    current_step = 4
    account_type = GROUP_ADMIN

    def get_success_url(self) -> str:
        return reverse_lazy("step_account_setup_red_teamer", kwargs={"organization_code": self.organization.code})

    def form_valid(self, form):
        name = form.cleaned_data["name"]
        self.add_success_notification(name)
        return super().form_valid(form)

    def add_success_notification(self, name):
        success_message = _("{name} successfully created.").format(name=name)
        messages.add_message(self.request, messages.SUCCESS, success_message)


class OnboardingAccountSetupRedTeamerView(
    RegistrationBreadcrumbsMixin,
    OnboardingAccountCreationMixin,
):
    """
    Step 2: Create an redteamer account with redteam rights
    """

    template_name = "account/step_5_account_setup_red_teamer.html"
    form_class = MemberRegistrationForm
    current_step = 4
    account_type = GROUP_REDTEAM

    def get_success_url(self, **kwargs):
        return reverse_lazy("step_account_setup_client", kwargs={"organization_code": self.organization.code})

    def form_valid(self, form):
        name = form.cleaned_data["name"]
        trusted_clearance_level = form.cleaned_data.get("trusted_clearance_level")
        if trusted_clearance_level and int(trusted_clearance_level) < DNS_REPORT_LEAST_CLEARANCE_LEVEL:
            clearance_level_warning_dns_report(self.request, trusted_clearance_level)
        self.add_success_notification(name)
        return super().form_valid(form)

    def add_success_notification(self, name):
        success_message = _("{name} successfully created.").format(name=name)
        messages.add_message(self.request, messages.SUCCESS, success_message)


class OnboardingAccountSetupClientView(RegistrationBreadcrumbsMixin, OnboardingAccountCreationMixin):
    """
    Step 3: Create a client account.
    """

    template_name = "account/step_6_account_setup_client.html"
    form_class = MemberRegistrationForm
    current_step = 4
    account_type = GROUP_CLIENT

    def get_success_url(self, **kwargs):
        return reverse_lazy("complete_onboarding", kwargs={"organization_code": self.organization.code})

    def form_valid(self, form):
        name = form.cleaned_data["name"]
        self.add_success_notification(name)
        return super().form_valid(form)

    def add_success_notification(self, name):
        success_message = _("{name} successfully created.").format(name=name)
        messages.add_message(self.request, messages.SUCCESS, success_message)


class CompleteOnboarding(OrganizationView):
    """
    Complete onboarding for redteamers and superusers.
    """

    def get(self, request, *args, **kwargs):
        self.organization_member.onboarded = True
        self.organization_member.status = OrganizationMember.STATUSES.ACTIVE
        self.organization_member.save()
        return redirect(reverse("crisis_room"))
