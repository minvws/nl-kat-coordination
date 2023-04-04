from django.contrib.auth import get_user_model

from tools.models import (
    Organization,
    OrganizationMember,
)

User = get_user_model()


def indemnification_present(user: User) -> bool:
    return user.indemnification_set.exists()


def can_scan_organization(user: User, organization: Organization) -> bool:
    member = OrganizationMember.objects.filter(user=user, organization=organization)

    if member[0].is_redteam:
        return True

    # Ensure the user is scanning its own organization
    if not member:
        return False

    return indemnification_present(user)


def can_switch_organization(user: User) -> bool:
    return user.has_perm("tools.can_switch_organization")
