from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from django.utils.safestring import mark_safe

phone_validator = RegexValidator(
    regex=r"^\+?1?\d{11,11}$",
    message="Phone number must be entered in the format: '+99999999999'. 11 digits allowed.",
)

password_validation_text = mark_safe(
    _(
        """
        <p>
        Password must contain the following:
        <ul>
            <li>Minimum length of 12 characters</li>
            <li>Minimum of 2 digits</li>
            <li>Minimum of 2 uppercase letters</li>
            <li>Minimum of 2 lowercase letters</li>
            <li>Minimum of 2 special characters</li>
        </ul>
        </p>
    """
    )
)
