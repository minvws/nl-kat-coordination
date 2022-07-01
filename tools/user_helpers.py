from typing import List

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from tools.models import (
    Organization,
    OrganizationMember,
    GROUP_ADMIN,
    GROUP_REDTEAM,
    GROUP_CLIENT,
)


def organizations_for_user(user: User) -> List[Organization]:
    if is_red_team(user):
        return Organization.objects.all()

    return [OrganizationMember.objects.get(user=user).organization]


def is_red_team(user: User) -> bool:
    return user.groups.filter(name="redteam").exists()


def is_admin(user: User) -> bool:
    return user.groups.filter(name="admin").exists()


def indemnification_present(user: User) -> bool:
    return user.indemnification_set.exists()


def can_scan_organization(user: User, organization: Organization) -> bool:
    if is_red_team(user):
        return True

    # Ensure the user is scanning its own organization
    if not OrganizationMember.objects.filter(
        user=user, organization=organization
    ).exists():
        return False

    return indemnification_present(user)


class SuperUserRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser


class AdminUserRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.groups.filter(name=GROUP_ADMIN).exists()


class RedTeamUserRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.groups.filter(name=GROUP_REDTEAM).exists()


class SuperOrAdminUserRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        is_admin = self.request.user.groups.filter(name=GROUP_ADMIN).exists()
        if self.request.user.is_superuser or is_admin:
            return True


def can_switch_organization(user: User) -> bool:
    return user.has_perm("tools.can_switch_organization")


class ClientNotAuthorizedMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return not self.request.user.groups.filter(name=GROUP_CLIENT).exists()


class CanViewMembersMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.has_perm("tools.view_organizationmember")

    def handle_no_permission(self):
        messages.add_message(
            self.request,
            messages.ERROR,
            _("You are not allowed to view organization members."),
        )

        if self.request.user.has_perm("tools.view_organization"):
            organization = self.get_object()
            return redirect(
                reverse("organization_detail", kwargs={"pk": organization.id})
            )

        return redirect("crisis_room")
