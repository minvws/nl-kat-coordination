from typing import Any, Dict, List, Type

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
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.urls.base import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView, FormView, UpdateView
from katalogus.client import get_katalogus
from tools.forms.boefje import SelectBoefjeForm
from tools.forms.ooi_form import OOIForm
from tools.models import GROUP_ADMIN, GROUP_CLIENT, GROUP_REDTEAM, Organization, OrganizationMember
from tools.ooi_helpers import (
    create_object_tree_item_from_ref,
    filter_ooi_tree,
    get_or_create_ooi,
)
from tools.view_helpers import Breadcrumb, BreadcrumbsMixin, get_ooi_url

from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import OOI
from octopoes.models.ooi.network import Network
from octopoes.models.types import type_by_name
from onboarding.forms import (
    OnboardingSetClearanceLevelForm,
)
from onboarding.view_helpers import (
    DNS_REPORT_LEAST_CLEARANCE_LEVEL,
    ONBOARDING_PERMISSIONS,
    KatIntroductionAdminStepsMixin,
    KatIntroductionRegistrationStepsMixin,
    KatIntroductionStepsMixin,
)
from rocky.bytes_client import get_bytes_client
from rocky.exceptions import (
    AcknowledgedClearanceLevelTooLowException,
    IndemnificationNotPresentException,
    RockyError,
    TrustedClearanceLevelTooLowException,
)
from rocky.messaging import clearance_level_warning_dns_report
from rocky.views.indemnification_add import IndemnificationAddView
from rocky.views.ooi_report import DNSReport, Report, build_findings_list_from_store
from rocky.views.ooi_view import BaseOOIDetailView, BaseOOIFormView, SingleOOITreeMixin

User = get_user_model()


class OnboardingBreadcrumbsMixin(BreadcrumbsMixin):
    def build_breadcrumbs(self):
        return [
            {
                "url": reverse_lazy("step_introduction", kwargs={"organization_code": self.organization.code}),
                "text": _("OpenKAT introduction"),
            },
        ]


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
    TemplateView,
):
    template_name = "step_1_introduction.html"
    current_step = 1
    permission_required = "tools.can_scan_organization"


class OnboardingChooseReportInfoView(
    OrganizationPermissionRequiredMixin,
    KatIntroductionStepsMixin,
    TemplateView,
):
    template_name = "step_2a_choose_report_info.html"
    current_step = 2
    permission_required = "tools.can_scan_organization"


class OnboardingChooseReportTypeView(
    OrganizationPermissionRequiredMixin,
    KatIntroductionStepsMixin,
    TemplateView,
):
    template_name = "step_2b_choose_report_type.html"
    current_step = 2
    permission_required = "tools.can_scan_organization"


class OnboardingSetupScanSelectPluginsView(
    OrganizationPermissionRequiredMixin,
    KatIntroductionStepsMixin,
    TemplateView,
):
    template_name = "step_3g_setup_scan_select_plugins.html"
    current_step = 3
    report: Type[Report] = DNSReport
    permission_required = "tools.can_enable_disable_boefje"

    def get_form(self):
        boefjes = self.report.get_boefjes(self.organization)
        boefjes = [boefje for boefje in boefjes if boefje["boefje"].scan_level <= DNS_REPORT_LEAST_CLEARANCE_LEVEL]
        kwargs = {
            "initial": {"boefje": [item["id"] for item in boefjes if item.get("required", False)]},
        }

        if self.request.method in ("POST", "PUT"):
            kwargs.update(
                {
                    "data": self.request.POST,
                }
            )

        return SelectBoefjeForm(boefjes=boefjes, organization=self.organization, **kwargs)

    def post(self, request, *args, **kwargs):
        if "ooi_id" not in request.GET:
            raise BadRequest("No OOI ID provided")
        ooi_id = request.GET["ooi_id"]

        form = self.get_form()
        if form.is_valid():
            if "boefje" in request.POST:
                data = form.cleaned_data
                request.session["selected_boefjes"] = data
            return redirect(get_ooi_url("step_setup_scan_ooi_detail", ooi_id, self.organization.code))
        return self.get(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["select_boefjes_form"] = self.get_form()
        return context


class OnboardingSetupScanOOIInfoView(
    OrganizationPermissionRequiredMixin,
    KatIntroductionStepsMixin,
    TemplateView,
):
    template_name = "step_3a_setup_scan_ooi_info.html"
    current_step = 3
    permission_required = "tools.can_scan_organization"


class OnboardingOOIForm(OOIForm):
    """
    hidden_fields - key (field name) value (field value) pair that will rendered as hidden field
    """

    def __init__(
        self, hidden_fields: Dict[str, str], ooi_class: Type[OOI], connector: OctopoesAPIConnector, *args, **kwargs
    ):
        self.hidden_ooi_fields = hidden_fields
        super().__init__(ooi_class, connector, *args, **kwargs)

    def get_fields(self):
        return self.generate_form_fields(self.hidden_ooi_fields)


class OnboardingSetupScanOOIAddView(
    OrganizationPermissionRequiredMixin,
    KatIntroductionStepsMixin,
    BaseOOIFormView,
):
    template_name = "step_3b_setup_scan_ooi_add.html"
    current_step = 3
    permission_required = "tools.can_scan_organization"
    form_class = OnboardingOOIForm
    hidden_form_fields = {
        "network": {
            "ooi": Network(name="internet"),
        }
    }

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.ooi_class = self.get_ooi_class()

    def get_hidden_form_fields(self):
        hidden_fields = {}
        bytes_client = get_bytes_client(self.organization.code)

        for field_name, params in self.hidden_form_fields.items():
            ooi, created = get_or_create_ooi(self.octopoes_api_connector, bytes_client, params["ooi"])
            hidden_fields[field_name] = ooi.primary_key

            if created:
                messages.success(
                    self.request,
                    _(
                        "OpenKAT added the following required object to your object list to complete your request: {}"
                    ).format(str(ooi)),
                )
        return hidden_fields

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        hidden_fields = self.get_hidden_form_fields()
        kwargs.update({"hidden_fields": hidden_fields, "initial": hidden_fields})

        return kwargs

    def get_ooi_class(self) -> Type[OOI]:
        try:
            return type_by_name(self.kwargs["ooi_type"])
        except KeyError:
            raise Http404("OOI not found")

    def get_ooi_success_url(self, ooi: OOI) -> str:
        self.request.session["ooi_id"] = ooi.primary_key
        return get_ooi_url("step_clearance_level_introduction", ooi.primary_key, self.organization.code)

    def build_breadcrumbs(self) -> List[Breadcrumb]:
        return super().build_breadcrumbs() + [
            {
                "url": reverse("ooi_add_type_select", kwargs={"organization_code": self.organization.code}),
                "text": _("Creating an object"),
            },
        ]

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["type"] = self.ooi_class.get_ooi_type()
        return context


class OnboardingSetupScanOOIDetailView(
    OrganizationPermissionRequiredMixin,
    SingleOOITreeMixin,
    KatIntroductionStepsMixin,
    OnboardingBreadcrumbsMixin,
    TemplateView,
):
    template_name = "step_3c_setup_scan_ooi_detail.html"
    current_step = 3
    permission_required = "tools.can_scan_organization"

    def get_ooi_id(self) -> str:
        if "ooi_id" in self.request.session:
            return self.request.session["ooi_id"]
        return super().get_ooi_id()

    def get(self, request, *args, **kwargs):
        self.ooi = self.get_ooi()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        ooi = self.get_ooi()
        level = DNS_REPORT_LEAST_CLEARANCE_LEVEL
        try:
            self.raise_clearance_level(ooi.reference, level)
        except IndemnificationNotPresentException:
            messages.add_message(
                self.request,
                messages.ERROR,
                _(
                    "Could not raise clearance level of %s to L%s. \
                Indemnification not present at organization %s."
                )
                % (
                    ooi.reference.human_readable,
                    level,
                    self.organization.name,
                ),
            )
            return self.get(request, *args, **kwargs)
        except TrustedClearanceLevelTooLowException:
            messages.add_message(
                self.request,
                messages.ERROR,
                _(
                    "Could not raise clearance level of %s to L%s. "
                    "You were trusted a clearance level of L%s. "
                    "Contact your administrator to receive a higher clearance."
                )
                % (
                    ooi.reference.human_readable,
                    level,
                    self.organization_member.acknowledged_clearance_level,
                ),
            )
            return self.get(request, *args, **kwargs)
        except AcknowledgedClearanceLevelTooLowException:
            messages.add_message(
                self.request,
                messages.ERROR,
                _(
                    "Could not raise clearance level of %s to L%s. "
                    "You acknowledged a clearance level of L%s. "
                    "Please accept the clearance level first on your profile page to proceed."
                )
                % (
                    ooi.reference.human_readable,
                    level,
                    self.organization_member.acknowledged_clearance_level,
                ),
            )
            return self.get(request, *args, **kwargs)

        self.enable_selected_boefjes()
        return redirect(get_ooi_url("step_report", self.get_ooi_id(), self.organization.code))

    def enable_selected_boefjes(self) -> None:
        if not self.request.session.get("selected_boefjes"):
            return
        for boefje_id in self.request.session["selected_boefjes"]:
            get_katalogus(self.organization.code).enable_boefje_by_id(boefje_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ooi"] = self.ooi
        return context


class OnboardingClearanceLevelIntroductionView(
    OrganizationPermissionRequiredMixin, KatIntroductionStepsMixin, OnboardingBreadcrumbsMixin, TemplateView
):
    template_name = "step_3d_clearance_level_introduction.html"
    permission_required = "tools.can_set_clearance_level"
    current_step = 3

    def get_boefjes_tiles(self):
        tiles = [
            {
                "id": "dns_zone",
                "type": "boefje",
                "scan_level": "l1",
                "name": "DNS-Zone",
                "description": "Fetch the parent DNS zone of a hostname",
                "enabled": False,
            },
            {
                "id": "fierce",
                "type": "boefje",
                "scan_level": "l3",
                "name": "Fierce",
                "description": "Finds subdomains by brute force",
                "enabled": False,
            },
        ]
        return tiles

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ooi"] = self.request.GET.get("ooi_id", None)
        context["boefjes"] = self.get_boefjes_tiles()
        return context


class OnboardingAcknowledgeClearanceLevelView(
    OrganizationPermissionRequiredMixin,
    KatIntroductionStepsMixin,
    OnboardingBreadcrumbsMixin,
    OOIClearanceMixin,
    TemplateView,
):
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
    FormView,
):
    template_name = "step_3f_set_clearance_level.html"
    form_class = OnboardingSetClearanceLevelForm
    permission_required = "tools.can_set_clearance_level"
    current_step = 3
    initial = {"level": DNS_REPORT_LEAST_CLEARANCE_LEVEL}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ooi"] = self.request.GET.get("ooi_id", None)
        context["dns_report_least_clearance_level"] = DNS_REPORT_LEAST_CLEARANCE_LEVEL
        return context

    def get_success_url(self, **kwargs):
        return get_ooi_url("step_setup_scan_select_plugins", self.request.GET.get("ooi_id"), self.organization.code)

    def form_valid(self, form):
        self.add_success_notification()
        return super().form_valid(form)

    def add_success_notification(self):
        success_message = _("Clearance level has been set")
        messages.add_message(self.request, messages.SUCCESS, success_message)


class OnboardingReportView(
    OrganizationPermissionRequiredMixin,
    KatIntroductionStepsMixin,
    TemplateView,
):
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


class BaseReportView(BaseOOIDetailView):
    report: Type[Report]
    depth = 15

    def get_tree_dict(self):
        return create_object_tree_item_from_ref(self.tree.root, self.tree.store)

    def get_filtered_tree(self, tree_dict):
        return filter_ooi_tree(tree_dict, self.report.get_ooi_type_filter())

    def get_findings_list(self):
        return build_findings_list_from_store(self.tree.store, self.report.get_finding_filter())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["findings_list"] = self.get_findings_list()
        context["tree"] = self.get_filtered_tree(self.get_tree_dict())
        return context


class DnsReportView(OrganizationPermissionRequiredMixin, OnboardingBreadcrumbsMixin, BaseReportView):
    template_name = "dns_report.html"
    permission_required = "tools.can_scan_organization"
    report = DNSReport


class RegistrationBreadcrumbsMixin(BreadcrumbsMixin):
    breadcrumbs = [
        {"url": reverse_lazy("step_introduction_registration"), "text": _("OpenKAT Setup")},
    ]


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
    OrganizationPermissionRequiredMixin, KatIntroductionAdminStepsMixin, TemplateView
):
    """
    Step 4: Split flow to or continue with single account or continue to multiple account creation
    """

    template_name = "account/step_2c_account_setup_intro.html"
    current_step = 4
    permission_required = "tools.add_organizationmember"


class OnboardingAccountCreationMixin(OrganizationPermissionRequiredMixin, KatIntroductionAdminStepsMixin, FormView):
    account_type = None
    permission_required = "tools.add_organizationmember"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization"] = self.organization
        kwargs["account_type"] = self.account_type
        return kwargs


# Account setup for multiple user accounts: redteam, admins, clients


class OnboardingChooseUserTypeView(OrganizationPermissionRequiredMixin, KatIntroductionAdminStepsMixin, TemplateView):
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
