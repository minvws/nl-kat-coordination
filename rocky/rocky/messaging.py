from django.contrib import messages
from django.utils.translation import gettext_lazy as _


def clearance_level_warning_dns_report(request, trusted_clearance_level):
    message = _(
        "You have trusted this member with a clearance level of L{}. "
        "This member needs at least a clearance level of L2 in order to do a proper onboarding. "
        "Edit this member and change the clearance level if necessary."
    ).format(trusted_clearance_level)
    messages.add_message(request, messages.WARNING, message)
