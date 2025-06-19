from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from reports.views.base import get_selection
from tools.models import Organization
from tools.view_helpers import Breadcrumb, BreadcrumbsMixin, StepsMixin

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
                "text": _("1: Welcome"),
                "url": reverse_lazy("step_1_introduction_registration") + get_selection(self.request),
            },
            {
                "text": _("2: Organization setup"),
                "url": reverse_lazy("step_2a_organization_setup", kwargs={"organization_code": self.organization.code})
                + get_selection(self.request),
            },
            {
                "text": _("3: Add object"),
                "url": reverse_lazy("step_5_add_scan_ooi", kwargs={"organization_code": self.organization.code})
                + get_selection(self.request),
            },
            {
                "text": _("4: Plugins"),
                "url": reverse_lazy("step_11_report", kwargs={"organization_code": self.organization.code})
                + get_selection(self.request),
            },
            {
                "text": _("5: Generating report"),
                "url": reverse_lazy("step_9_choose_report_type", kwargs={"organization_code": self.organization.code})
                + get_selection(self.request),
            },
        ]
        return steps


class IntroductionRegistrationStepsMixin(StepsMixin):
    organization: Organization

    def build_steps(self):
        steps = [
            {"text": _("1: Introduction"), "url": reverse_lazy("step_1_introduction_registration")},
            {"text": _("2: Organization setup"), "url": reverse_lazy("step_2a_organization_setup")},
            {"text": _("3: Add object"), "url": "step_5_add_scan_ooi"},
            {"text": _("4: Plugins"), "url": "step_7_clearance_level_introduction"},
            {"text": _("5: Generating report"), "url": "step_9_choose_report_type"},
        ]
        return steps


class IntroductionAdminStepsMixin(StepsMixin):
    organization: Organization

    def build_steps(self):
        steps = [
            {"text": _("1: Introduction"), "url": reverse_lazy("step_1_introduction_registration")},
            {"text": _("2: Organization setup"), "url": reverse_lazy("step_2a_organization_setup")},
            {
                "text": _("3: Add object"),
                "url": reverse_lazy(
                    "step_3_indemnification_setup", kwargs={"organization_code": self.organization.code}
                ),
            },
            {
                "text": _("4: Plugins"),
                "url": reverse_lazy(
                    "step_7_clearance_level_introduction", kwargs={"organization_code": self.organization.code}
                ),
            },
            {
                "text": _("5: Generating report"),
                "url": reverse_lazy(
                    "step_9_choose_report_type"  # , kwargs={"organization_code": self.organization.code}
                ),
            },
        ]
        return steps


class OnboardingBreadcrumbsMixin(BreadcrumbsMixin):
    organization: Organization

    def build_breadcrumbs(self) -> list[Breadcrumb]:
        return [{"url": reverse_lazy("step_1_introduction_registration"), "text": _("OpenKAT introduction")}]


class RegistrationBreadcrumbsMixin(BreadcrumbsMixin):
    breadcrumbs = [{"url": reverse_lazy("step_1_introduction_registration"), "text": _("OpenKAT Setup")}]
