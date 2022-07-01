from typing import Optional

from django import forms
from django.contrib.auth import forms as auth_forms
from django.core.mail import send_mail
from django.utils.translation import gettext_lazy as _

from tools.forms import BaseRockyForm
from tools.models import User


class RecoverUsernameForm(BaseRockyForm):
    recover_email = forms.EmailField(
        label=_("Email address"),
        max_length=254,
        help_text=_("Your username will be sent to this email"),
    )

    def get_username(self) -> Optional[str]:
        try:
            recover_username = User.objects.get(
                email__exact=self.cleaned_data["recover_email"]
            ).get_username()

            return recover_username
        except User.DoesNotExist:
            return None

    def send_username_to_recover_mail(self):
        # to do: check email templates (HTML)
        username = self.get_username()
        if username is not None:
            subject = "Recover Username"
            message = "Your username is: " + username
            send_mail(
                subject,
                message,
                from_email=None,
                recipient_list=[self.cleaned_data["recover_email"]],
                fail_silently=False,
            )


class PasswordResetForm(auth_forms.PasswordResetForm):
    email = forms.EmailField(
        label=_("Email address"),
        max_length=254,
        help_text=_("A reset link will be sent to this email"),
        widget=forms.TextInput(
            attrs={"placeholder": "The email address connected to your KAT-account"}
        ),
    )
