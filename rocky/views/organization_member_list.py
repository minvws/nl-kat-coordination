from enum import Enum
from typing import List
from django.contrib import messages
from django.shortcuts import redirect
from django.urls.base import reverse
from django.views.generic import DetailView
from requests.exceptions import RequestException
from django_otp.decorators import otp_required
from two_factor.views.utils import class_view_decorator
from django.contrib.auth.mixins import PermissionRequiredMixin
from tools.enums import SCAN_LEVEL
from tools.models import Organization, OrganizationMember
from tools.view_helpers import OrganizationMemberBreadcrumbsMixin


class PageActions(Enum):
    GIVE_CLEARANCE = "give_clearance"
    WITHDRAW_CLEARANCE = "withdraw_clearance"


@class_view_decorator(otp_required)
class OrganizationMemberListView(
    PermissionRequiredMixin,
    OrganizationMemberBreadcrumbsMixin,
    DetailView,
):
    model = Organization
    template_name = "organizations/organization_member_list.html"
    filters_active: List[str] = []
    permission_required = "tools.view_organizationmember"

    def post(self, request, *args, **kwargs):
        if "action" not in self.request.POST:
            return self.get(request, *args, **kwargs)

        self.object = self.get_object()
        self.handle_page_action(request.POST.get("action"))

        return redirect(reverse("organization_member_list", kwargs={"pk": self.kwargs.get("pk")}))

    def handle_page_action(self, action: str):
        try:
            member_id = self.request.POST.get("member_id")
            new_trusted_level = max(
                [scan_level.value for scan_level in SCAN_LEVEL]
            )  # This will be set in the form in the future, but for now we hardcode it.
            organizationmember = OrganizationMember.objects.get(id=member_id)
            if action == PageActions.GIVE_CLEARANCE.value:
                # If the newly assigned "trusted level" is lower than the previous trusted and acknowledged level,
                # we lower the acknowledged level to the newly assigned level.
                if new_trusted_level < organizationmember.acknowledged_clearance_level:
                    organizationmember.acknowledged_clearance_level = new_trusted_level
                organizationmember.trusted_clearance_level = new_trusted_level
            elif action == PageActions.WITHDRAW_CLEARANCE.value:
                organizationmember.trusted_clearance_level = 0
                organizationmember.acknowledged_clearance_level = 0
            else:
                raise Exception(f"Unhandled allowed action: {action}")
            organizationmember.save()
        except RequestException as exception:
            messages.add_message(self.request, messages.ERROR, f"{action} failed: '{exception}'")

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.filters_active = self.get_filters_active()

    def get_queryset(self):
        """
        List organization that only belongs to user that requests the list.
        """
        object = self.model.objects.filter(code=self.request.user.organizationmember.organization.code)
        return object

    def get_filters_active(self):
        return self.request.GET.getlist("client_status", [])

    def get_checkbox_filters(self):
        return [
            {
                "label": choice[0],
                "value": choice[1],
                "checked": not self.filters_active or choice[0] in self.filters_active,
            }
            for choice in OrganizationMember.STATUSES.choices
        ]

    def get_members(self):
        member_set = self.object.members
        if self.filters_active:
            member_set = member_set.filter(status__in=self.filters_active)

        return member_set.all()

    def build_breadcrumbs(self):
        self.set_breadcrumb_object(self.object)
        return super().build_breadcrumbs()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["members"] = self.get_members()
        context["checkbox_filters"] = self.get_checkbox_filters()
        return context
