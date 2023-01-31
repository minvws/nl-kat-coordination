from typing import Type, List, Dict, Any

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import BadRequest
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.urls.base import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView, FormView, UpdateView
from django_otp.decorators import otp_required
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import OOI
from octopoes.models.ooi.network import Network
from octopoes.models.types import type_by_name
from two_factor.views.utils import class_view_decorator

from account.forms import OrganizationForm, OrganizationUpdateForm
from account.mixins import OrganizationView
from katalogus.client import get_katalogus
from onboarding.forms import (
    OnboardingCreateUserAdminForm,
    OnboardingCreateUserRedTeamerForm,
    OnboardingCreateUserClientForm,
    OnboardingSetClearanceLevelForm,
)
from onboarding.mixins import RedTeamUserRequiredMixin, SuperOrAdminUserRequiredMixin
from onboarding.view_helpers import (
    KatIntroductionStepsMixin,
    KatIntroductionAdminStepsMixin,
    KatIntroductionRegistrationStepsMixin,
)
from rocky.exceptions import IndemnificationNotPresentException, ClearanceLevelTooLowException
from rocky.views.indemnification_add import IndemnificationAddView
from rocky.views.ooi_report import Report, DNSReport, build_findings_list_from_store
from rocky.views.ooi_view import BaseOOIFormView, SingleOOITreeMixin, BaseOOIDetailView
from tools.forms.boefje import SelectBoefjeForm
from tools.models import Organization, OrganizationMember
from tools.ooi_form import OOIForm
from tools.ooi_helpers import (
    get_or_create_ooi,
    create_object_tree_item_from_ref,
    filter_ooi_tree,
)
from tools.user_helpers import is_red_team
from tools.view_helpers import get_ooi_url, BreadcrumbsMixin, Breadcrumb

User = get_user_model()


class OnboardingBreadcrumbsMixin(BreadcrumbsMixin, OrganizationView):
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
        if is_red_team(request.user):
            return redirect("step_introduction", kwargs={"organization_code": self.organization.code})
        return redirect("crisis_room")


# REDTEAMER FLOW
@class_view_decorator(otp_required)
class OnboardingIntroductionView(
    RedTeamUserRequiredMixin,
    KatIntroductionStepsMixin,
    TemplateView,
):
    template_name = "step_1_introduction.html"
    current_step = 1


@class_view_decorator(otp_required)
class OnboardingChooseReportInfoView(
    RedTeamUserRequiredMixin,
    KatIntroductionStepsMixin,
    TemplateView,
):
    template_name = "step_2a_choose_report_info.html"
    current_step = 2


@class_view_decorator(otp_required)
class OnboardingChooseReportTypeView(
    RedTeamUserRequiredMixin,
    KatIntroductionStepsMixin,
    TemplateView,
):
    template_name = "step_2b_choose_report_type.html"
    current_step = 2


@class_view_decorator(otp_required)
class OnboardingSetupScanSelectPluginsView(
    RedTeamUserRequiredMixin,
    KatIntroductionStepsMixin,
    TemplateView,
):
    template_name = "step_3e_setup_scan_select_plugins.html"
    current_step = 3
    report: Type[Report] = DNSReport

    def get_form(self):
        boefjes = self.report.get_boefjes(self.organization)
        boefjes = [
            boefje for boefje in boefjes if boefje["boefje"].scan_level <= int(self.request.session["clearance_level"])
        ]
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


@class_view_decorator(otp_required)
class OnboardingSetupScanOOIInfoView(
    RedTeamUserRequiredMixin,
    KatIntroductionStepsMixin,
    TemplateView,
):
    template_name = "step_3a_setup_scan_ooi_info.html"
    current_step = 3


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


@class_view_decorator(otp_required)
class OnboardingSetupScanOOIAddView(
    RedTeamUserRequiredMixin,
    KatIntroductionStepsMixin,
    BaseOOIFormView,
):
    template_name = "step_3b_setup_scan_ooi_add.html"
    current_step = 3
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
        for field_name, params in self.hidden_form_fields.items():
            ooi, created = get_or_create_ooi(self.octopoes_api_connector, params["ooi"])
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

    def get_success_url(self, ooi: OOI) -> str:
        self.request.session["ooi_id"] = ooi.primary_key
        return get_ooi_url("step_set_clearance_level", ooi.primary_key, self.organization.code)

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


@class_view_decorator(otp_required)
class OnboardingSetupScanOOIDetailView(
    RedTeamUserRequiredMixin,
    SingleOOITreeMixin,
    KatIntroductionStepsMixin,
    OnboardingBreadcrumbsMixin,
    TemplateView,
):
    template_name = "step_3c_setup_scan_ooi_detail.html"
    current_step = 3

    def get_ooi_id(self) -> str:
        if "ooi_id" in self.request.session:
            return self.request.session["ooi_id"]
        return super().get_ooi_id()

    def get(self, request, *args, **kwargs):
        self.ooi = self.get_ooi()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):

        ooi = self.get_ooi()
        level = int(self.request.session["clearance_level"])
        try:
            self.raise_clearance_level(ooi.reference, level)
        except (IndemnificationNotPresentException, ClearanceLevelTooLowException):
            return self.get(request, *args, **kwargs)

        self.enable_selected_boefjes()
        return redirect(get_ooi_url("step_report", self.get_ooi_id(), self.organization.code))

    def enable_selected_boefjes(self) -> None:
        if not self.request.session.get("selected_boefjes"):
            return
        for boefje_id in self.request.session["selected_boefjes"]:
            get_katalogus(self.organization.code).enable_boefje(boefje_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ooi"] = self.ooi
        return context


@class_view_decorator(otp_required)
class OnboardingSetClearanceLevelView(
    RedTeamUserRequiredMixin,
    KatIntroductionStepsMixin,
    OnboardingBreadcrumbsMixin,
    FormView,
):
    template_name = "step_3d_set_clearance_level.html"
    form_class = OnboardingSetClearanceLevelForm
    current_step = 3
    initial = {"level": 2}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["boefjes"] = self.get_boefjes_tiles()
        return context

    def get_success_url(self, **kwargs):
        return get_ooi_url("step_setup_scan_select_plugins", self.request.GET.get("ooi_id"), self.organization.code)

    def form_valid(self, form):
        self.request.session["clearance_level"] = form.cleaned_data["level"]
        self.add_success_notification()
        return super().form_valid(form)

    def add_success_notification(self):
        success_message = _("Clearance level has been set")
        messages.add_message(self.request, messages.SUCCESS, success_message)

    def get_boefje_cover_img(self, boefje_id):
        return reverse("plugin_cover", kwargs={"plugin_id": boefje_id, "organization_code": self.organization.code})

    def get_boefjes_tiles(self):
        tiles = [
            {
                "tile_image": self.get_boefje_cover_img("dns_zone"),
                "scan_level": "l1",
                "name": "DNS-Zone",
                "description": "Fetch the parent DNS zone of a hostname",
            },
            {
                "tile_image": self.get_boefje_cover_img("fierce"),
                "scan_level": "l3",
                "name": "Fierce",
                "description": "Finds subdomains by brute force",
            },
        ]
        return tiles


@class_view_decorator(otp_required)
class OnboardingReportView(
    RedTeamUserRequiredMixin,
    KatIntroductionStepsMixin,
    TemplateView,
):
    template_name = "step_4_report.html"
    current_step = 4

    def post(self, request, *args, **kwargs):
        if "ooi_id" not in request.GET:
            raise BadRequest("No OOI ID provided")
        ooi_id = request.GET["ooi_id"]

        self.set_member_onboarded()
        return redirect(get_ooi_url("dns_report", ooi_id, self.organization.code))

    def set_member_onboarded(self):
        member = OrganizationMember.objects.get(user=self.request.user, organization=self.organization)
        member.onboarded = True
        member.save()


class BaseReportView(RedTeamUserRequiredMixin, BaseOOIDetailView):
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


@class_view_decorator(otp_required)
class DnsReportView(OnboardingBreadcrumbsMixin, BaseReportView):
    template_name = "dns_report.html"
    report = DNSReport

    def get_dns_zone_for_url(self):
        """
        Path to DNSZone: url > hostnamehttpurl > netloc > fqdn > dns_zone
        """
        if self.ooi.ooi_type != "URL":
            return self.ooi

        try:
            web_url = self.tree.store[str(self.ooi.web_url)]
            netloc = self.tree.store[str(web_url.netloc)]
            fqdn = self.tree.store[str(netloc.fqdn)]
            dns_zone = super().get_ooi(pk=str(fqdn.dns_zone))
            return dns_zone
        except KeyError:
            messages.add_message(self.request, messages.ERROR, _("No DNS zone found."))
            return self.ooi


class RegistrationBreadcrumbsMixin(BreadcrumbsMixin):
    breadcrumbs = [
        {"url": reverse_lazy("step_introduction_registration"), "text": _("OpenKAT Setup")},
    ]


# account flow
@class_view_decorator(otp_required)
class OnboardingIntroductionRegistrationView(
    SuperOrAdminUserRequiredMixin, KatIntroductionRegistrationStepsMixin, TemplateView
):
    """
    Step: 1 - Registration introduction
    """

    template_name = "account/step_1_registration_intro.html"
    current_step = 1


@class_view_decorator(otp_required)
class OnboardingOrganizationSetupView(
    SuperOrAdminUserRequiredMixin,
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

    def get(self, request, *args, **kwargs):
        organization = Organization.objects.first()
        if organization:
            self.get_or_create_organizationmember(organization)
            return redirect(reverse("step_organization_update", kwargs={"organization_code": organization.code}))
        return super().get(request, *args, **kwargs)

    def get_success_url(self) -> str:
        organization = Organization.objects.first()
        self.get_or_create_organizationmember(organization)
        return reverse_lazy("step_indemnification_setup", kwargs={"organization_code": organization.code})

    def form_valid(self, form):
        org_name = form.cleaned_data["name"]
        self.add_success_notification(org_name)
        return super().form_valid(form)

    def get_or_create_organizationmember(self, organization):
        if self.request.user.is_superuser:
            OrganizationMember.objects.get_or_create(
                user=self.request.user,
                organization=organization,
                trusted_clearance_level=4,
                acknowledged_clearance_level=4,
            )
        else:
            OrganizationMember.objects.get_or_create(user=self.request.user, organization=organization)

    def add_success_notification(self, org_name):
        success_message = _("{org_name} succesfully created.").format(org_name=org_name)
        messages.add_message(self.request, messages.SUCCESS, success_message)


@class_view_decorator(otp_required)
class OnboardingOrganizationUpdateView(
    SuperOrAdminUserRequiredMixin,
    KatIntroductionAdminStepsMixin,
    UpdateView,
):
    """
    Step 2: Update an existing organization (only name not code)
    """

    model = Organization
    template_name = "account/step_2a_organization_update.html"
    form_class = OrganizationUpdateForm
    current_step = 2

    def get_object(self, queryset=None):
        return self.organization

    def get_success_url(self) -> str:
        return reverse_lazy("step_indemnification_setup", kwargs={"organization_code": self.organization.code})

    def form_valid(self, form):
        org_name = form.cleaned_data["name"]
        self.add_success_notification(org_name)
        return super().form_valid(form)

    def add_success_notification(self, org_name):
        success_message = _("{org_name} succesfully updated.").format(org_name=org_name)
        messages.add_message(self.request, messages.SUCCESS, success_message)


@class_view_decorator(otp_required)
class OnboardingIndemnificationSetupView(
    SuperOrAdminUserRequiredMixin,
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


@class_view_decorator(otp_required)
class OnboardingAccountSetupIntroView(SuperOrAdminUserRequiredMixin, KatIntroductionAdminStepsMixin, TemplateView):
    """
    Step 4: Split flow to or continue with single account or continue to multiple account creation
    """

    template_name = "account/step_2c_account_setup_intro.html"
    current_step = 4


@class_view_decorator(otp_required)
class OnboardingAccountCreationMixin(SuperOrAdminUserRequiredMixin, KatIntroductionAdminStepsMixin, CreateView):
    """ """

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organization_code"] = self.organization.code
        return kwargs


# Account setup for multiple user accounts: redteam, admins, clients
@class_view_decorator(otp_required)
class OnboardingChooseUserTypeView(KatIntroductionAdminStepsMixin, TemplateView):
    """
    Step 1: Introduction about how to create multiple user accounts
    """

    current_step = 4
    template_name = "account/step_3_account_user_type.html"


@class_view_decorator(otp_required)
class OnboardingAccountSetupAdminView(
    RegistrationBreadcrumbsMixin,
    OnboardingAccountCreationMixin,
):
    """
    Step 1: Create an admin account with admin rights
    """

    model = User
    template_name = "account/step_4_account_setup_admin.html"
    form_class = OnboardingCreateUserAdminForm
    current_step = 4

    def get_success_url(self) -> str:
        return reverse_lazy("step_account_setup_red_teamer", kwargs={"organization_code": self.organization.code})

    def form_valid(self, form):
        name = form.cleaned_data["name"]
        self.add_success_notification(name)
        return super().form_valid(form)

    def add_success_notification(self, name):
        success_message = _("{name} succesfully created.").format(name=name)
        messages.add_message(self.request, messages.SUCCESS, success_message)


@class_view_decorator(otp_required)
class OnboardingAccountSetupRedTeamerView(
    RegistrationBreadcrumbsMixin,
    OnboardingAccountCreationMixin,
):

    """
    Step 2: Create an redteamer account with redteam rights
    """

    model = User
    template_name = "account/step_5_account_setup_red_teamer.html"
    form_class = OnboardingCreateUserRedTeamerForm
    current_step = 4

    def get_success_url(self, **kwargs):
        return reverse_lazy("step_account_setup_client", kwargs={"organization_code": self.organization.code})

    def form_valid(self, form):
        name = form.cleaned_data["name"]
        self.add_success_notification(name)
        return super().form_valid(form)

    def add_success_notification(self, name):
        success_message = _("{name} succesfully created.").format(name=name)
        messages.add_message(self.request, messages.SUCCESS, success_message)


@class_view_decorator(otp_required)
class OnboardingAccountSetupClientView(RegistrationBreadcrumbsMixin, OnboardingAccountCreationMixin):
    """
    Step 3: Create a client account.
    """

    model = User
    template_name = "account/step_6_account_setup_client.html"
    form_class = OnboardingCreateUserClientForm
    current_step = 4

    def get_success_url(self, **kwargs):
        return reverse_lazy("crisis_room")

    def form_valid(self, form):
        name = form.cleaned_data["name"]
        self.add_success_notification(name)
        return super().form_valid(form)

    def add_success_notification(self, name):
        success_message = _("{name} succesfully created.").format(name=name)
        messages.add_message(self.request, messages.SUCCESS, success_message)


@class_view_decorator(otp_required)
class CompleteOnboarding(OrganizationView):
    """
    Complete onboarding for redteamers and superusers.
    """

    def get(self, request, *args, **kwargs):
        member, _ = OrganizationMember.objects.get_or_create(user=request.user, organization=self.organization)
        redteam_group = Group.objects.get(name="redteam")
        if self.request.user.is_superuser and redteam_group not in self.request.user.groups.all():
            redteam_group.user_set.add(self.request.user)
            return redirect(reverse("step_introduction", kwargs={"organization_code": self.organization.code}))
        member.onboarded = True
        member.save()
        return redirect(reverse("crisis_room"))
