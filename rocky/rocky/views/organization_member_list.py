from enum import Enum

from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls.base import reverse
from django.views.generic import ListView
from django_otp.decorators import otp_required
from requests.exceptions import RequestException
from tools.models import OrganizationMember
from tools.view_helpers import OrganizationMemberBreadcrumbsMixin
from two_factor.views.utils import class_view_decorator


class PageActions(Enum):
    BLOCK = "block"
    UNBLOCK = "unblock"


@class_view_decorator(otp_required)
class OrganizationMemberListView(
    PermissionRequiredMixin,
    OrganizationMemberBreadcrumbsMixin,
    ListView,
):
    model = OrganizationMember
    context_object_name = "members"
    template_name = "organizations/organization_member_list.html"
    permission_required = "tools.view_organization"

    def get_queryset(self):
        queryset = self.model.objects.filter(organization=self.organization)
        if "client_status" in self.request.GET:
            status_filter = self.request.GET.getlist("client_status", [])
            queryset = self.filter_queryset(queryset, status_filter)
        return queryset

    def filter_queryset(self, queryset, blocked_status_filter):
        return [member for member in queryset if member.status in blocked_status_filter]

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.filters_active = self.get_filters_active()

    def post(self, request, *args, **kwargs):
        if not self.request.user.has_perms("tools.change_organizationmember"):
            raise PermissionDenied()
        if "action" not in self.request.POST:
            return self.get(request, *args, **kwargs)
        self.handle_page_action(request.POST.get("action"))
        return redirect(reverse("organization_member_list", kwargs={"organization_code": self.organization.code}))

    def handle_page_action(self, action: str):
        member_id = self.request.POST.get("member_id")
        organizationmember = self.model.objects.get(id=member_id)
        try:
            if action == PageActions.BLOCK.value:
                organizationmember.status = OrganizationMember.STATUSES.BLOCKED
            elif action == PageActions.UNBLOCK.value:
                organizationmember.status = OrganizationMember.STATUSES.ACTIVE
            else:
                raise Exception(f"Unhandled allowed action: {action}")
            organizationmember.save()
        except RequestException as exception:
            messages.add_message(self.request, messages.ERROR, f"{action} failed: '{exception}'")

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["checkbox_filters"] = self.get_checkbox_filters()
        return context
