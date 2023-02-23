from enum import Enum

from django.contrib import messages
from django.shortcuts import redirect
from django.urls.base import reverse
from django.views.generic import ListView
from django_otp.decorators import otp_required
from requests.exceptions import RequestException
from two_factor.views.utils import class_view_decorator

from tools.enums import SCAN_LEVEL
from tools.models import OrganizationMember
from tools.view_helpers import OrganizationMemberBreadcrumbsMixin


class PageActions(Enum):
    GIVE_CLEARANCE = "give_clearance"
    WITHDRAW_CLEARANCE = "withdraw_clearance"
    VERIFY = "verify"
    UNVERIFY = "unverify"


@class_view_decorator(otp_required)
class OrganizationMemberListView(
    OrganizationMemberBreadcrumbsMixin,
    ListView,
):
    model = OrganizationMember
    context_object_name = "members"

    def get_queryset(self):
        queryset = self.model.objects.filter(organization=self.organization)
        if "verified_status_filter" in self.request.GET:
            verified_status_filter = self.request.GET.getlist("verified_status_filter", [])
            queryset = self.filter_queryset(queryset, verified_status_filter)
        for member in queryset:
            if member.user.is_superuser:
                member.verified = True
        return queryset

    def filter_queryset(self, queryset, verified_status_filter):
        result = []
        if "verified" in verified_status_filter:
            result += [member for member in queryset if member.verified]
        if "unverified" in verified_status_filter:
            result += [member for member in queryset if not member.verified]
        return result

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if "action" not in self.request.POST:
            return self.get(request, *args, **kwargs)
        self.handle_page_action(request.POST.get("action"))
        return redirect(reverse("organization_detail", kwargs={"organization_code": self.organization.code}))

    def handle_page_action(self, action: str):
        member_id = self.request.POST.get("member_id")
        organizationmember = self.model.objects.get(id=member_id)
        try:
            new_trusted_level = max(
                [scan_level.value for scan_level in SCAN_LEVEL]
            )  # This will be set in the form in the future, but for now we hardcode it.
            if action == PageActions.GIVE_CLEARANCE.value:
                # If the newly assigned "trusted level" is lower than the previous trusted and acknowledged level,
                # we lower the acknowledged level to the newly assigned level.
                if new_trusted_level < organizationmember.acknowledged_clearance_level:
                    organizationmember.acknowledged_clearance_level = new_trusted_level
                organizationmember.trusted_clearance_level = new_trusted_level
            elif action == PageActions.WITHDRAW_CLEARANCE.value:
                organizationmember.trusted_clearance_level = 0
                organizationmember.acknowledged_clearance_level = 0
            elif action == PageActions.VERIFY.value:
                organizationmember.verified = True
            elif action == PageActions.UNVERIFY.value:
                organizationmember.verified = False
            else:
                raise Exception(f"Unhandled allowed action: {action}")
            organizationmember.save()
        except RequestException as exception:
            messages.add_message(self.request, messages.ERROR, f"{action} failed: '{exception}'")

    def get_verified_filters(self):
        return [
            {
                "label": "Verified",
                "value": "verified",
                "checked": "verified_status_filter" not in self.request.GET
                or "verified" in self.request.GET.getlist("verified_status_filter", []),
            },
            {
                "label": "Unverified",
                "value": "unverified",
                "checked": "verified_status_filter" not in self.request.GET
                or "unverified" in self.request.GET.getlist("verified_status_filter", []),
            },
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["verified_filters"] = self.get_verified_filters()
        return context
