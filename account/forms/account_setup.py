from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth import forms as auth_forms
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from rocky.settings import MIAUW_API_ENABLED
from tools.forms import DataListInput, BaseRockyForm
from tools.models import (
    GROUP_CLIENT,
    GROUP_ADMIN,
    GROUP_REDTEAM,
    Organization,
    OrganizationMember,
)
from django.contrib.auth.password_validation import validate_password
from account.validators import get_password_validators_help_texts

User = get_user_model()


class GroupAddForm(forms.Form):
    """Add group dropdown field to form"""

    GROUP_CHOICES = [
        ("", _("--- Please select one of the available options ----")),
        (GROUP_ADMIN, GROUP_ADMIN),
        (GROUP_REDTEAM, GROUP_REDTEAM),
        (GROUP_CLIENT, GROUP_CLIENT),
    ]

    account_type = forms.CharField(
        label=_("Account Type"),
        help_text=_("Every member of KAT must be part of a group."),
        error_messages={
            "group": {
                "required": _("Please select a group to proceed."),
            },
        },
        widget=forms.Select(
            choices=GROUP_CHOICES,
            attrs={
                "aria-describedby": "explanation-account-type",
            },
        ),
    )


class IndemnificationAddForm(BaseRockyForm):
    may_scan = forms.CharField(
        label=_(
            "I declare that KAT may scan the assets of my organization and I am aware of the risk the extra load on my systems will bring."
        ),
        widget=forms.CheckboxInput(),
    )
    am_authorized = forms.CharField(
        label=_(
            "I declare that I am authorized to give this indemnification within my organization."
        ),
        widget=forms.CheckboxInput(),
    )


class UserAddForm(forms.Form):
    """
    Basic User form fields, name, email and password.
    With fields validation.
    """

    name = forms.CharField(
        label=_("Name"),
        max_length=254,
        help_text=_("This name we will use to communicate with you."),
        widget=forms.TextInput(
            attrs={
                "autocomplete": "off",
                "placeholder": _("What do we call you?"),
                "aria-describedby": "explanation-name",
            }
        ),
    )
    email = forms.EmailField(
        label=_("Email"),
        max_length=254,
        help_text=_("Enter your email address."),
        widget=forms.EmailInput(
            attrs={
                "autocomplete": "off",
                "placeholder": "name@example.com",
                "aria-describedby": "explanation-email",
            }
        ),
    )
    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "off",
                "placeholder": _("Choose your super secret password"),
                "aria-describedby": "explanation-password",
            }
        ),
        help_text=get_password_validators_help_texts(),
        validators=[validate_password],
    )

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email=email).exists():
            self.add_error("email", _("Choose another email."))
        return email

    def set_user(self):
        self.user = User.objects.create_user(
            email=self.cleaned_data["email"],
            password=self.cleaned_data["password"],
        )


class OrganizationMemberAddForm(UserAddForm, forms.ModelForm):
    """
    Form to add a new member
    """

    group = None

    def __init__(self, *args, **kwargs):
        if "organization_name" in kwargs:
            self.organization = self.get_organization_with_name(
                kwargs.pop("organization_name")
            )
        elif "organization_id" in kwargs:
            self.organization = self.get_organization_with_id(
                kwargs.pop("organization_id")
            )
        return super().__init__(*args, **kwargs)

    def get_organization_with_id(self, id):
        return Organization.objects.get(pk=id)

    def get_organization_with_name(self, organization_name):
        return Organization.objects.get(name=organization_name)

    def set_organization_member(self):
        OrganizationMember.objects.get_or_create(
            user=self.user,
            organization=self.organization,
            verified=True,
            member_name=self.cleaned_data["name"],
        )

    def save(self, **kwargs):
        if self.group:
            selected_group = Group.objects.get(name=self.group)
        else:
            selected_group = Group.objects.get(name=self.cleaned_data["account_type"])
        if self.organization and selected_group:
            self.set_user()
            self.set_organization_member()
            selected_group.user_set.add(self.user)
            self.user.save()


class OrganizationMemberToGroupAddForm(GroupAddForm, OrganizationMemberAddForm):
    class Meta:
        model = User
        fields = ("account_type", "name", "email", "password")


class OrganizationMemberForm(forms.ModelForm):
    class Meta:
        model = OrganizationMember
        fields = ["status"]

        def __init__(self, *args, **kwargs):
            if MIAUW_API_ENABLED:
                self.fields.append("signal_username")

            super().__init__(*args, **kwargs)


class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ["name"]

        def __init__(self, *args, **kwargs):
            if MIAUW_API_ENABLED:
                self.fields.append("signal_username")
                self.widgets["signal_username"] = DataListInput()

            super().__init__(*args, **kwargs)

    def __init__(self, signal_username_choices=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if signal_username_choices and "signal_username" in self.fields:
            self.fields["signal_username"].widget.choices = signal_username_choices

    def clean_signal_username(self):
        data = self.cleaned_data["signal_username"]

        # you can only change signal_username when no group has been created yet
        if data != self.instance.signal_username and self.instance.signal_group_id:
            raise ValidationError(
                _("Unable to change signal username, once a group has been created.")
            )

        return data


class SetPasswordForm(auth_forms.SetPasswordForm):
    """
    A form that lets a user change set their password without entering the old
    password
    """

    error_messages = {
        "password_mismatch": _("The two password fields didn’t match."),
    }
    new_password1 = forms.CharField(
        label=_("New password"),
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "placeholder": _("Enter your new password"),
            }
        ),
        strip=False,
        help_text=get_password_validators_help_texts,
        validators=[validate_password],
    )
    new_password2 = forms.CharField(
        label=_("New password confirmation"),
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "placeholder": _("Repeat your new password"),
            }
        ),
        help_text=_("Confirm your new password"),
        validators=[validate_password],
    )
