from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpRequest
from django.shortcuts import get_object_or_404, redirect
from django_otp.decorators import otp_required
from requests import RequestException

from rocky.settings import MIAUW_API_ENABLED
from tools.miauw_helpers import receive_last_messages
from tools.models import OrganizationMember, Organization
from tools.user_helpers import can_switch_organization


def get_organization(request: HttpRequest):
    if "client_id" in request.GET:
        return get_object_or_404(OrganizationMember, pk=request.GET.get("client_id")).organization

    return get_object_or_404(Organization, pk=request.GET.get("organization_id"))


@otp_required
@user_passes_test(can_switch_organization)
def switch_client(request: HttpRequest):
    organization = get_organization(request)

    if request.session["active_organization_id"] == organization.id:
        messages.add_message(request, messages.WARNING, "Could not switch. Already using organization.")
    else:
        messages.add_message(request, messages.INFO, "Switched to: " + organization.name)

    request.session["active_organization_id"] = organization.id

    try:
        if MIAUW_API_ENABLED and organization.has_signal_group():
            receive_last_messages(organization.signal_username)
    except RequestException as exception:
        messages.add_message(request, messages.WARNING, str(exception))

    return redirect("organization_list")
