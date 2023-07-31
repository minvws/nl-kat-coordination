from enum import Enum

from account.mixins import OrganizationPermissionRequiredMixin
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import models
from django.shortcuts import redirect
from django.urls.base import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView
from requests.exceptions import RequestException
from tools.models import OrganizationMember
from tools.view_helpers import OrganizationMemberBreadcrumbsMixin


class BLOCK_STATUSES(models.TextChoices):
    BLOCKED = _("Blocked"), "blocked"
    UNBLOCKED = _("Not blocked"), "unblocked"


class PageActions(Enum):
    BLOCK = "block"
    UNBLOCK = "unblock"


class OrganizationMemberListView(
    OrganizationPermissionRequiredMixin,
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
            queryset = [member for member in queryset if member.status in status_filter]

        if "blocked_status" in self.request.GET:
            blocked_filter = self.request.GET.getlist("blocked_status", [])
            blocked_filter_bools = []

            # Conversion from string values to boolean values
            for filter_option in blocked_filter:
                if filter_option == "blocked":
                    blocked_filter_bools.append(True)
                if filter_option == "unblocked":
                    blocked_filter_bools.append(False)

            queryset = [member for member in queryset if member.blocked in blocked_filter_bools]
        return queryset

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.filters_active = self.get_filters_active()

    def post(self, request, *args, **kwargs):
        if not self.organization_member.has_perm("tools.change_organizationmember"):
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
                organizationmember.blocked = True
                messages.add_message(
                    self.request,
                    messages.SUCCESS,
                    _("Blocked member %s successfully.") % (organizationmember.user.email),
                )
            elif action == PageActions.UNBLOCK.value:
                organizationmember.blocked = False
                messages.add_message(
                    self.request,
                    messages.SUCCESS,
                    _("Unblocked member %s successfully.") % (organizationmember.user.email),
                )
            else:
                raise Exception(f"Unhandled allowed action: {action}")
            organizationmember.save()
        except RequestException as exception:
            messages.add_message(self.request, messages.ERROR, f"{action} failed: '{exception}'")

    def get_filters_active(self):
        active_filters = self.request.GET.getlist("client_status", [])
        active_filters += [item.lower() for item in self.request.GET.getlist("blocked_status", [])]
        return active_filters

    def get_status_filters(self):
        return [
            {
                "label": choice[0],
                "value": choice[1],
                "checked": not self.filters_active or choice[0] in self.filters_active,
            }
            for choice in OrganizationMember.STATUSES.choices
        ]

    def get_blocked_filters(self):
        return [
            {
                "label": choice[0],
                "value": choice[1],
                "checked": not self.filters_active or choice[1] in self.filters_active,
            }
            for choice in BLOCK_STATUSES.choices
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_filters"] = self.get_status_filters()
        context["blocked_filters"] = self.get_blocked_filters()

        return context
