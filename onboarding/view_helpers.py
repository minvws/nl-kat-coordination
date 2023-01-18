from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from account.mixins import OrganizationView
from tools.view_helpers import StepsMixin


class KatIntroductionStepsMixin(StepsMixin, OrganizationView):
    def build_steps(self):
        steps = [
            {
                "text": _("1: Introduction"),
                "url": reverse_lazy("step_introduction", kwargs={"organization_code": self.organization.code}),
            },
            {
                "text": _("2: Choose a report"),
                "url": reverse_lazy("step_choose_report_info", kwargs={"organization_code": self.organization.code}),
            },
            {
                "text": _("3: Setup scan"),
                "url": reverse_lazy("step_setup_scan_ooi_info", kwargs={"organization_code": self.organization.code}),
            },
            {
                "text": _("4: Open report"),
                "url": reverse_lazy("step_report", kwargs={"organization_code": self.organization.code}),
            },
        ]
        return steps


class KatIntroductionRegistrationStepsMixin(StepsMixin):
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


class KatIntroductionAdminStepsMixin(StepsMixin, OrganizationView):
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
