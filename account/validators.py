from django.utils.translation import gettext as _
from django.utils.html import format_html, format_html_join
from rocky.settings import AUTH_PASSWORD_VALIDATORS


def get_password_validators_help_texts():
    """
    Set password help_texts especially for Manon.
    """
    help_texts = []
    validators = {}
    explanation = _("Your password must contain at least the following:")
    for validator in AUTH_PASSWORD_VALIDATORS:
        validators.update(validator["OPTIONS"])
    help_texts += [
        str(validators["min_length"]) + _(" characters"),
        str(validators["min_length_digit"]) + _(" digits"),
        str(validators["min_length_alpha"]) + _(" letters"),
        str(validators["min_length_special"])
        + _(" special characters such as: ")
        + str(validators["special_characters"]),
        str(validators["min_length_lower"]) + _(" lower case letters"),
        str(validators["min_length_upper"]) + _(" upper case letters"),
    ]
    help_text_builder = format_html_join(
        "", "<li>{}</li>", ((help_text,) for help_text in help_texts)
    )
    return (
        format_html("<p>{}</p><ul>{}</ul>", explanation, help_text_builder)
        if help_text_builder
        else ""
    )
