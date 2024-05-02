from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from reports.views.base import get_selection
from tools.models import Organization
from tools.view_helpers import BreadcrumbsMixin, StepsMixin

ONBOARDING_PERMISSIONS = (
    "tools.can_scan_organization",
    "tools.can_set_clearance_level",
    "tools.can_enable_disable_boefje",
)

DNS_REPORT_LEAST_CLEARANCE_LEVEL = 1


class IntroductionStepsMixin(StepsMixin):
    organization: Organization

    def build_steps(self):
        steps = [
            {
                "text": _("1: Introduction"),
                "url": reverse_lazy("step_introduction", kwargs={"organization_code": self.organization.code})
                + get_selection(self.request),
            },
            {
                "text": _("2: Choose a report"),
                "url": reverse_lazy("step_choose_report_info", kwargs={"organization_code": self.organization.code})
                + get_selection(self.request),
            },
            {
                "text": _("3: Setup scan"),
                "url": reverse_lazy("step_setup_scan_ooi_info", kwargs={"organization_code": self.organization.code})
                + get_selection(self.request),
            },
            {
                "text": _("4: Open report"),
                "url": reverse_lazy("step_report", kwargs={"organization_code": self.organization.code})
                + get_selection(self.request),
            },
        ]
        return steps


class IntroductionRegistrationStepsMixin(StepsMixin):
    organization: Organization

    def build_steps(self):
        steps = [
            {
                "text": _("1: Introduction"),
                "url": reverse_lazy("step_introduction_registration"),
            },
            {
                "text": _("2: Organization setup"),
                "url": reverse_lazy("step_organization_setup"),
            },
            {"text": _("3: Indemnification"), "url": ""},
            {"text": _("4: Account setup"), "url": ""},
        ]
        return steps


class IntroductionAdminStepsMixin(StepsMixin):
    organization: Organization

    def build_steps(self):
        steps = [
            {
                "text": _("1: Introduction"),
                "url": reverse_lazy("step_introduction_registration"),
            },
            {
                "text": _("2: Organization setup"),
                "url": reverse_lazy("step_organization_setup"),
            },
            {
                "text": _("3: Indemnification"),
                "url": reverse_lazy("step_indemnification_setup", kwargs={"organization_code": self.organization.code}),
            },
            {
                "text": _("4: Account setup"),
                "url": reverse_lazy("step_account_setup_intro", kwargs={"organization_code": self.organization.code}),
            },
        ]
        return steps


class OnboardingBreadcrumbsMixin(BreadcrumbsMixin):
    organization: Organization

    def build_breadcrumbs(self):
        return [
            {
                "url": reverse_lazy("step_introduction", kwargs={"organization_code": self.organization.code}),
                "text": _("OpenKAT introduction"),
            },
        ]


class RegistrationBreadcrumbsMixin(BreadcrumbsMixin):
    breadcrumbs = [
        {"url": reverse_lazy("step_introduction_registration"), "text": _("OpenKAT Setup")},
    ]
