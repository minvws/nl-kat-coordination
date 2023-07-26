from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from tools.forms.settings import SCAN_LEVEL_CHOICES

User = get_user_model()


class ClearanceLevelSelect(forms.Select):
    """Only level 2 is enabled in onboarding flow"""

    def create_option(self, *args, **kwargs):
        option = super().create_option(*args, **kwargs)
        if option.get("value") != 2:
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
