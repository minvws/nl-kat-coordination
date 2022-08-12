from typing import List
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from tools.models import (
    Organization,
    OrganizationMember,
)

User = get_user_model()


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


def can_switch_organization(user: User) -> bool:
    return user.has_perm("tools.can_switch_organization")
