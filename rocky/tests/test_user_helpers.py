from tools.models import OrganizationMember
from tools.user_helpers import (
    organizations_for_user,
    is_red_team,
    is_admin,
    indemnification_present,
    can_scan_organization,
    can_switch_organization,
)


def test_organizations_for_user(my_user):
    result = organizations_for_user(my_user)
    assert len(result) == 1


def test_organizations_for_red_teamer(my_red_teamer):
    result = organizations_for_user(my_red_teamer)
    assert len(result) == 1


def test_is_not_red_team(my_user):
    assert not is_red_team(my_user)


def test_is_red_team(my_red_teamer):
    assert is_red_team(my_red_teamer)


def test_is_not_admin(my_user):
    assert not is_admin(my_user)


def test_is_admin(my_red_teamer):
    assert is_admin(my_red_teamer)


def test_indemnification_present(my_user):
    assert indemnification_present(my_user)


def test_can_scan_organization(my_user, organization):
    assert can_scan_organization(my_user, organization)

    member = OrganizationMember.objects.get(user=my_user, organization=organization)
    assert member.delete()

    assert not can_scan_organization(my_user, organization)


def test_red_teamer_can_scan_organization(my_red_teamer, organization):
    assert can_scan_organization(my_red_teamer, organization)


def test_can_switch_organization(my_user):
    assert can_switch_organization(my_user)
