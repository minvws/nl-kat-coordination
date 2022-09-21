from datetime import datetime, timezone
from typing import Type, List, Dict, Any
from django.contrib.auth.models import Group
from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.urls.base import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView, FormView, UpdateView
from django_otp.decorators import otp_required
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import DeclaredScanProfile
from octopoes.models import OOI
from octopoes.models.ooi.network import Network
from octopoes.models.types import type_by_name
from two_factor.views.utils import class_view_decorator
from django.contrib.auth import get_user_model
from onboarding.forms import (
    OnboardingCreateOrganizationForm,
    OnboardingCreateUserAdminForm,
    OnboardingCreateUserRedTeamerForm,
    OnboardingCreateUserClientForm,
    OnboardingSetClearanceLevelForm,
)
from onboarding.view_helpers import (
    KatIntroductionStepsMixin,
    KatIntroductionAdminStepsMixin,
)
from katalogus.client import get_katalogus
from rocky.views import BaseOOIFormView
from rocky.views.ooi_view import SingleOOITreeMixin, BaseOOIDetailView
from tools.forms import SelectBoefjeForm
from tools.models import Organization, OrganizationMember
from tools.ooi_form import OOIForm
from tools.ooi_helpers import (
    get_or_create_ooi,
    create_object_tree_item_from_ref,
    filter_ooi_tree,
)
from tools.user_helpers import (
    is_admin,
    is_red_team,
)
from onboarding.mixins import RedTeamUserRequiredMixin, SuperOrAdminUserRequiredMixin
from tools.view_helpers import get_ooi_url, BreadcrumbsMixin, Breadcrumb
from rocky.views.ooi_report import Report, DNSReport, build_findings_list_from_store

User = get_user_model()


class OnboardingBreadcrumbsMixin(BreadcrumbsMixin):
    breadcrumbs = [
        {"url": reverse_lazy("step_introduction"), "text": _("KAT introduction")},
    ]


def index(request):
    if request.user.is_superuser:
        return redirect("step_introduction_registration")
    if is_red_team(request.user):
        return redirect("step_introduction")
    return redirect("crisis_room")


@class_view_decorator(otp_required)
class OnboardingIntroductionView(
    RedTeamUserRequiredMixin,
    KatIntroductionStepsMixin,
    OnboardingBreadcrumbsMixin,
    TemplateView,
):
    template_name = "step_1_introduction.html"
    current_step = 1


@class_view_decorator(otp_required)
class OnboardingChooseReportInfoView(
    RedTeamUserRequiredMixin,
    KatIntroductionStepsMixin,
    OnboardingBreadcrumbsMixin,
    TemplateView,
):
    template_name = "step_2a_choose_report_info.html"
    current_step = 2


@class_view_decorator(otp_required)
class OnboardingChooseReportTypeView(
    RedTeamUserRequiredMixin,
    KatIntroductionStepsMixin,
    OnboardingBreadcrumbsMixin,
    TemplateView,
):
    template_name = "step_2b_choose_report_type.html"
    current_step = 2


@class_view_decorator(otp_required)
class OnboardingSetupScanSelectPluginsView(
    RedTeamUserRequiredMixin,
    KatIntroductionStepsMixin,
    OnboardingBreadcrumbsMixin,
    TemplateView,
):
    template_name = "step_3e_setup_scan_select_plugins.html"
    current_step = 3
    report: Type[Report] = DNSReport

    def get_form(self):
        boefjes = self.report.get_boefjes(self.request.active_organization)
        kwargs = {
            "boefjes": [
                boefje
                for boefje in boefjes
                if boefje["boefje"].scan_level
                <= int(self.request.session["clearance_level"])
            ],
            "initial": {
                "boefje": [
                    item["id"] for item in boefjes if item.get("required", False)
                ]
            },
        }
        if self.request.method in ("POST", "PUT"):
            kwargs.update(
                {
                    "data": self.request.POST,
                }
            )

        return SelectBoefjeForm(**kwargs)

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            if "boefje" in request.POST:
                data = form.cleaned_data
                request.session["selected_boefjes"] = data
            return redirect(
                get_ooi_url(
                    "step_setup_scan_ooi_detail", self.request.GET.get("ooi_id")
                )
            )
        return self.get(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        # context["xxxboefjes"] = self.report.get_boefjes()
        context["select_boefjes_form"] = self.get_form()
        return context


@class_view_decorator(otp_required)
class OnboardingSetupScanOOIInfoView(
    RedTeamUserRequiredMixin,
    KatIntroductionStepsMixin,
    OnboardingBreadcrumbsMixin,
    TemplateView,
):
    template_name = "step_3a_setup_scan_ooi_info.html"
    current_step = 3


class OnboardingOOIForm(OOIForm):
    """
    hidden_fields - key (field name) value (field value) pair that will rendered as hidden field
    """

    def __init__(
        self,
        hidden_fields: Dict[str, str],
        ooi_class: Type[OOI],
        connector: OctopoesAPIConnector,
        *args,
        **kwargs
    ):
        self.hidden_ooi_fields = hidden_fields
        super().__init__(ooi_class, connector, *args, **kwargs)

    def get_fields(self):
        return self.generate_form_fields(self.hidden_ooi_fields)


@class_view_decorator(otp_required)
class OnboardingSetupScanOOIAddView(
    RedTeamUserRequiredMixin,
    KatIntroductionStepsMixin,
    OnboardingBreadcrumbsMixin,
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
            ooi, created = get_or_create_ooi(self.api_connector, params["ooi"])
            hidden_fields[field_name] = ooi.primary_key

            if created:
                messages.success(
                    self.request,
                    _(
                        "KAT added the following required object to your object list to complete your request: {}"
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
        return get_ooi_url("step_set_clearance_level", ooi.primary_key)

    def build_breadcrumbs(self) -> List[Breadcrumb]:
        return super().build_breadcrumbs() + [
            {
                "url": reverse("ooi_add_type_select"),
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
        self.api_connector = self.get_api_connector()
        self.ooi = self.get_ooi()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.set_clearance_level()
        self.enable_selected_boefjes()
        return redirect(get_ooi_url("step_report", self.get_ooi_id()))

    def set_clearance_level(self):
        self.api_connector = self.get_api_connector()
        ooi = self.get_ooi()
        self.api_connector.save_scan_profile(
            DeclaredScanProfile(
                reference=ooi.reference, level=self.request.session["clearance_level"]
            ),
            valid_time=datetime.now(timezone.utc),
        )

    def enable_selected_boefjes(self) -> None:
        if not self.request.session.get("selected_boefjes"):
            return

        organization = self.request.user.organizationmember.organization
        for boefje_id in self.request.session["selected_boefjes"]:
            get_katalogus(organization.code).enable_boefje(boefje_id)

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
        return get_ooi_url(
            "step_setup_scan_select_plugins", self.request.GET.get("ooi_id")
        )

    def form_valid(self, form):
        self.request.session["clearance_level"] = form.data["level"]
        self.add_success_notification()
        return super().form_valid(form)

    def add_success_notification(self):
        success_message = _("Clearance level has been set")
        messages.add_message(self.request, messages.SUCCESS, success_message)

    def get_boefje_cover_img(self, boefje_id):
        return reverse("boefje_cover", kwargs={"boefje_id": boefje_id})

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
    OnboardingBreadcrumbsMixin,
    TemplateView,
):
    template_name = "step_4_report.html"
    current_step = 4

    def get(self, request, *args, **kwargs):
        self.set_current_stepper_url(
            get_ooi_url("step_report", self.request.GET.get("ooi_id"))
        )
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.set_member_onboarded()
        return redirect(get_ooi_url("dns_report", self.request.GET.get("ooi_id")))

    def set_member_onboarded(self):
        member = self.request.user.organizationmember
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
        return build_findings_list_from_store(
            self.tree.store, self.report.get_finding_filter()
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["findings_list"] = self.get_findings_list()
        context["tree"] = self.get_filtered_tree(self.get_tree_dict())
        return context


@class_view_decorator(otp_required)
class DnsReportView(OnboardingBreadcrumbsMixin, BaseReportView):
    template_name = "dns_report.html"
    report = DNSReport

    def get_ooi(self):
        return self.get_dns_zone_for_url(super().get_ooi())

    def get_dns_zone_for_url(self, ooi: OOI):
        """
        Path to DNSZone: url > hostnamehttpurl > netloc > fqdn > dns_zone
        """
        if ooi.ooi_type != "URL":
            return ooi

        try:
            web_url = self.tree.store[str(ooi.web_url)]
            netloc = self.tree.store[str(web_url.netloc)]
            fqdn = self.tree.store[str(netloc.fqdn)]
            dns_zone = super().get_ooi(str(fqdn.dns_zone))
            return dns_zone
        except KeyError:
            messages.add_message(self.request, messages.ERROR, _("No DNS zone found."))
            return ooi


class RegistrationBreadcrumbsMixin(BreadcrumbsMixin):
    breadcrumbs = [
        {"url": reverse_lazy("step_introduction_registration"), "text": _("KAT Setup")},
    ]


# account flow
@class_view_decorator(otp_required)
class OnboardingIntroductionRegistrationView(
    SuperOrAdminUserRequiredMixin, KatIntroductionAdminStepsMixin, TemplateView
):
    """
    Registration introduction
    """

    template_name = "account/step_1_registration_intro.html"
    current_step = 1


class OrganizationSessionMixin:
    def get_initial(self):
        if self.session_exists():
            self.initial["name"] = self.request.session["organization_name"]
        return self.initial

    def session_exists(self):
        if "organization_name" in self.request.session:
            return True

    def get_organization_id(self):
        try:
            organization = self.model.objects.get(
                name=self.request.session["organization_name"]
            )
        except:
            return None
        return organization.id

    def form_valid(self, form):
        self.request.session["organization_name"] = form.cleaned_data["name"]
        self.add_success_notification()
        return super().form_valid(form)

    def add_success_notification(self):
        success_message = _("Organization succesfully set.")
        messages.add_message(self.request, messages.SUCCESS, success_message)


@class_view_decorator(otp_required)
class OnboardingOrganizationSetupView(
    SuperOrAdminUserRequiredMixin,
    OrganizationSessionMixin,
    KatIntroductionAdminStepsMixin,
    UpdateView,
):
    """
    View to update the name of a organization
    """

    model = Organization
    template_name = "account/step_2_organization_setup.html"
    form_class = OnboardingCreateOrganizationForm
    current_step = 2
    success_url = reverse_lazy("step_choose_user_type")

    def dispatch(self, request, *args, **kwargs):
        organization_id = self.get_organization_id()
        if self.session_exists() and organization_id:
            return redirect(
                reverse(
                    "step_organization_update",
                    kwargs={"pk": organization_id},
                )
            )
        if is_admin(self.request.user):
            self.add_message()
            return redirect("step_account_setup_admin")
        else:
            return super().dispatch(request, *args, **kwargs)

    def get_object(self):
        obj = self.model.objects.get(code="_dev")
        return obj

    def add_success_notification(self):
        success_message = _("Organization succesfully created.")
        messages.add_message(self.request, messages.SUCCESS, success_message)

    def add_message(self):
        message = _(
            "Hello, admin. You are already part of an organization. Early step is skipped."
        )
        messages.add_message(self.request, messages.INFO, message)


@class_view_decorator(otp_required)
class OnboardingOrganizationUpdateView(
    SuperOrAdminUserRequiredMixin,
    OrganizationSessionMixin,
    KatIntroductionAdminStepsMixin,
    UpdateView,
):
    """
    View to update an existing organization.
    """

    model = Organization
    template_name = "account/step_2_organization_update.html"
    form_class = OnboardingCreateOrganizationForm
    current_step = 2
    success_url = reverse_lazy("step_choose_user_type")

    def add_success_notification(self):
        success_message = _("Organization succesfully updated.")
        messages.add_message(self.request, messages.SUCCESS, success_message)


@class_view_decorator(otp_required)
class OnboardingChooseUserTypeView(KatIntroductionAdminStepsMixin, TemplateView):
    current_step = 3
    template_name = "account/step_2a_account_user_type.html"


@otp_required
def make_superuser_redteamer(request):
    if request.user.is_superuser:
        redteam_group = Group.objects.get(name="redteam")
        redteam_group.user_set.add(request.user)
        return redirect(reverse("step_introduction"))


@otp_required
def skip_onboarding(request):
    member = OrganizationMember.objects.get(user=request.user)
    member.onboarded = True
    member.save()
    return redirect(reverse("crisis_room"))


@class_view_decorator(otp_required)
class OnboardingAccountSetupIntroView(
    SuperOrAdminUserRequiredMixin, KatIntroductionAdminStepsMixin, TemplateView
):
    template_name = "account/step_3_account_setup_intro.html"
    current_step = 3


@class_view_decorator(otp_required)
class OnboardingAccountCreationMixin(
    SuperOrAdminUserRequiredMixin, KatIntroductionAdminStepsMixin, CreateView
):
    current_step = 3

    def dispatch(self, request, *args, **kwargs):
        if (
            "organization_name" not in self.request.session
            and self.request.user.is_superuser
        ):
            self.add_error_notification()
            return redirect("step_organization_setup")
        else:
            return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if self.request.user.is_superuser:
            kwargs["organization_name"] = self.request.session["organization_name"]
        else:
            kwargs["organization_name"] = self.request.active_organization
        return kwargs

    def form_valid(self, form):
        self.add_success_notification()
        return super().form_valid(form)

    def add_success_notification(self):
        success_message = _("User succesfully created.")
        messages.add_message(self.request, messages.SUCCESS, success_message)

    def add_error_notification(self):
        info_message = _(
            "System Administrator: You are redirected to this page, because you have to first setup an organization."
        )
        messages.add_message(self.request, messages.INFO, info_message)


@class_view_decorator(otp_required)
class OnboardingAccountSetupAdminView(
    RegistrationBreadcrumbsMixin,
    OnboardingAccountCreationMixin,
):
    """
    View to create a new admin account
    """

    model = User
    template_name = "account/step_4_account_setup_admin.html"
    form_class = OnboardingCreateUserAdminForm

    def get_success_url(self, **kwargs):
        return reverse_lazy("step_account_setup_red_teamer")


@class_view_decorator(otp_required)
class OnboardingAccountSetupRedTeamerView(
    RegistrationBreadcrumbsMixin,
    OnboardingAccountCreationMixin,
):

    """
    View to create a red team account
    """

    model = User
    template_name = "account/step_5_account_setup_red_teamer.html"
    form_class = OnboardingCreateUserRedTeamerForm

    def get_success_url(self, **kwargs):
        return reverse_lazy("step_account_setup_client")


@class_view_decorator(otp_required)
class OnboardingAccountSetupClientView(
    RegistrationBreadcrumbsMixin, OnboardingAccountCreationMixin
):
    """
    View to create a client account
    """

    model = User
    template_name = "account/step_6_account_setup_client.html"
    form_class = OnboardingCreateUserClientForm
    succcess_url = reverse_lazy("step_account_setup_client")

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)

        # Since this step is optional there is no harm done in setting the
        # "onboarded" bool at setup time.
        member = OrganizationMember.objects.get(user=self.request.user)
        member.onboarded = True
        member.save()

    def get_success_url(self, **kwargs):
        return reverse_lazy("crisis_room")
