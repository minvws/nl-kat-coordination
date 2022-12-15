from enum import Enum
from typing import Dict, Any, List, Optional

from django.contrib import messages
from django.shortcuts import redirect
from django.urls.base import reverse
from django.views.generic import DetailView
from django_otp.decorators import otp_required
from requests.exceptions import RequestException
from two_factor.views.utils import class_view_decorator
from django.contrib.auth.mixins import PermissionRequiredMixin
from rocky.settings import MIAUW_API_ENABLED
from tools.miauw import SignalGroupResponse
from tools.miauw_helpers import (
    get_signal_group_for_organization,
    send_message_to_signal_group_for_organization,
    add_member_to_signal_group_for_organization,
    create_signal_group_for_organization,
)
from tools.models import Organization
from tools.view_helpers import Breadcrumb, OrganizationBreadcrumbsMixin


class PageActions(Enum):
    SIGNAL_GROUP_CREATE = "signal_group_create"
    SIGNAL_GROUP_ADD_MEMBER = "signal_group_add_member"
    SIGNAL_GROUP_SEND_TEST_MESSAGE = "signal_group_send_test_message"
    GIVE_CLEARANCE = "give_clearance"


def is_allowed_action_for_organization(action: PageActions, organization: Organization) -> bool:
    if not MIAUW_API_ENABLED:
        return False

    if action == PageActions.SIGNAL_GROUP_CREATE:
        return organization.signal_group_id is None

    if action == PageActions.SIGNAL_GROUP_ADD_MEMBER:
        return organization.signal_group_id is not None and organization.signal_username

    if action == PageActions.SIGNAL_GROUP_SEND_TEST_MESSAGE:
        return organization.signal_group_id is not None and organization.signal_username

    return False


def get_allowed_actions(organization) -> Dict[str, bool]:
    return {action.value: is_allowed_action_for_organization(action, organization) for action in PageActions}


@class_view_decorator(otp_required)
class OrganizationDetailView(
    PermissionRequiredMixin,
    OrganizationBreadcrumbsMixin,
    DetailView,
):
    model = Organization
    object: Organization = None  # type: ignore
    template_name = "organizations/organization_detail.html"
    permission_required = "tools.view_organization"

    def get_queryset(self):
        """
        List organization that only belongs to user that requests the list.
        """
        object = self.model.objects.filter(code=self.request.user.organizationmember.organization.code)
        return object

    def build_breadcrumbs(self) -> List[Breadcrumb]:
        breadcrumbs = super().build_breadcrumbs()

        breadcrumbs.append(
            {
                "url": reverse("organization_detail", kwargs={"pk": self.object.id}),
                "text": self.object.name,
            },
        )

        return breadcrumbs

    def get_signal_group(self) -> Optional[SignalGroupResponse]:
        if not MIAUW_API_ENABLED:
            return None

        try:
            return get_signal_group_for_organization(self.object)
        except RequestException as exception:
            messages.add_message(self.request, messages.WARNING, str(exception))

    def get_organization_members(self) -> List[Dict[str, Any]]:
        filters_active = self.request.GET.getlist("client_status", [])
        signal_group = self.get_signal_group()
        organization_members_set = self.object.members

        if filters_active:
            organization_members_set = organization_members_set.filter(status__in=filters_active)

        organization_members = [
            {
                "id": member.id,
                "member_name": member.member_name,
                "signal_username": member.signal_username,
                "is_in_signal_group": signal_group and member.signal_username in signal_group.members,
            }
            for member in organization_members_set.all()
        ]

        return organization_members

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)

        context["organization_members"] = self.get_organization_members()
        context["actions_allowed"] = get_allowed_actions(self.object)
        context["signal_group"] = self.get_signal_group()

        return context

    def post(self, request, *args, **kwargs):
        if "action" not in self.request.POST:
            return self.get(request, *args, **kwargs)

        self.object = self.get_object()
        self.handle_page_action(request.POST.get("action"))

        return redirect(reverse("organization_detail", kwargs={"pk": self.kwargs.get("pk")}))

    def handle_page_action(self, action):
        if action not in get_allowed_actions(self.object):
            messages.add_message(self.request, messages.WARNING, "Action not allowed: " + action)
            return self.get(self.request)

        try:
            if action == PageActions.SIGNAL_GROUP_CREATE.value:
                signal_group = create_signal_group_for_organization(self.object)
                self.object.signal_group_id = signal_group.id
                self.object.save()

                messages.add_message(
                    self.request,
                    messages.INFO,
                    "Saved signal group: " + signal_group.id,
                )
            elif action == PageActions.SIGNAL_GROUP_ADD_MEMBER.value:
                member_signal_username = self.request.POST.get("signal_username")
                add_member_to_signal_group_for_organization(self.object, member_signal_username)

                messages.add_message(
                    self.request,
                    messages.INFO,
                    "Added to signal group: " + member_signal_username,
                )
            elif action == PageActions.SIGNAL_GROUP_SEND_TEST_MESSAGE.value:
                send_message_to_signal_group_for_organization(self.object, "This is a test message sent by KAT.")

                messages.add_message(self.request, messages.INFO, "Test message sent.")
            else:
                raise Exception("Unhandled allowed action: " + action)
        except RequestException as exception:
            messages.add_message(self.request, messages.ERROR, f"{action} failed: '{exception}'")
