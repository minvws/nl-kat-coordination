from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from tools.forms.settings import SCAN_LEVEL_CHOICES

from onboarding.view_helpers import DNS_REPORT_LEAST_CLEARANCE_LEVEL

User = get_user_model()


class ClearanceLevelSelect(forms.Select):
    """A custom clearance level selection, disabling some clearance levels"""

    def create_option(self, *args, **kwargs):
        option = super().create_option(*args, **kwargs)
        if option.get("value") != DNS_REPORT_LEAST_CLEARANCE_LEVEL:
            option["attrs"]["disabled"] = "disabled"
        return option


class OnboardingSetClearanceLevelForm(forms.Form):
    level = forms.IntegerField(
        label=_("Clearance level"),
        help_text=_(
            "Boefjes that has a scan level below or equal to the clearance level, is permitted to scan an object."
        ),
        error_messages={
            "level": {
                "required": _("Please select a clearance level to proceed."),
            },
        },
        widget=ClearanceLevelSelect(
            choices=SCAN_LEVEL_CHOICES,
            attrs={
                "aria-describedby": _("explanation-clearance-level"),
            },
        ),
    )
