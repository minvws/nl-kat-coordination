from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _
from account.validators import get_password_validators_help_texts


class LoginForm(AuthenticationForm):
    """
    This is an adaptation of the login form of django's AuthenticationForm
    This form is also part of the two-factor authentication flow.
    """

    error_messages = {
        "invalid_login": _("Please enter a correct email address and password."),
        "inactive": _("This account is inactive."),
    }

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].help_text = _(
            "Insert the email you registered with or got at KAT installation."
        )
