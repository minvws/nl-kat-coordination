from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.utils.translation import gettext_lazy as _
from tools.models import (
    Organization,
    SCAN_LEVEL,
    GROUP_ADMIN,
    GROUP_REDTEAM,
    GROUP_CLIENT,
    OrganizationMember,
)
from tools.forms import BLANK_CHOICE
from account.forms import OrganizationMemberAddForm

User = get_user_model()


class ClearanceLevelSelect(forms.Select):
    """Only level 2 is enabled in onboarding flow"""

    def create_option(self, *args, **kwargs):
        option = super().create_option(*args, **kwargs)
        if not option.get("value") == 2:
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
            choices=[BLANK_CHOICE] + SCAN_LEVEL.choices,
            attrs={
                "aria-describedby": _("explanation-clearance-level"),
            },
        ),
    )


class OnboardingCreateOrganizationForm(forms.ModelForm):
    """
    Form to create a new organization for admins, red teamers and clients
    """

    class Meta:
        model = Organization
        fields = [
            "name",
        ]

        labels = {
            "name": _("Name"),
        }
        help_texts = {
            "name": _("What is the name of your organization."),
        }
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "placeholder": _("The name of the organization this KAT account is for."),
                    "autocomplete": "off",
                    "aria-describedby": _("explanation-organization-name"),
                },
            ),
        }
        error_messages = {
            "name": {
                "required": _("Organization name is required to proceed."),
                "unique": _("Choose another organization."),
            },
        }


class OnboardingUserForm(OrganizationMemberAddForm):
    """
    This is the standard form model that is used across all onboarding
    user account creation.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.check_permissions()

    def check_permissions(self):
        if self.group:
            permission = Permission.objects.get(codename="can_set_clearance_level")
            group_object = Group.objects.filter(name=self.group, permissions=permission.id)

        if group_object:
            self.fields["trusted_clearance_level"] = forms.BooleanField(
                label=_("Trusted to set clearance levels on OOI's"),
                widget=forms.CheckboxInput(),
                help_text=_("Give this user permission to set clearance levels on OOI's"),
                required=False,
            )

    class Meta:
        model = OrganizationMember
        fields = ("name", "email", "password")


class OnboardingCreateUserAdminForm(OnboardingUserForm):
    """
    To create an admin account, only superusers and admins
    have this permission.
    """

    group = GROUP_ADMIN


class OnboardingCreateUserRedTeamerForm(OnboardingUserForm):
    """
    Form to create a red teamer user.
    """

    group = GROUP_REDTEAM


class OnboardingCreateUserClientForm(OnboardingUserForm):
    """
    Form to create a client user.
    """

    group = GROUP_CLIENT
