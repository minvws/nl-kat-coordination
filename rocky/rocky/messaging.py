from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from onboarding.view_helpers import DNS_REPORT_LEAST_CLEARANCE_LEVEL


def clearance_level_warning_dns_report(request, trusted_clearance_level):
    message = _(
        "You have trusted this member with a clearance level of L{}. "
        "This member needs at least a clearance level of L{} in order to do a proper onboarding. "
        "Edit this member and change the clearance level if necessary."
    ).format(trusted_clearance_level, DNS_REPORT_LEAST_CLEARANCE_LEVEL)
    messages.add_message(request, messages.WARNING, message)
