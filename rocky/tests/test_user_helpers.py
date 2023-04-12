from tools.user_helpers import (
    is_red_team,
    is_admin,
    indemnification_present,
    can_scan_organization,
    can_switch_organization,
)


def test_is_not_red_team(superuser_member):
    assert not is_red_team(superuser_member.user)


def test_is_red_team(redteam_member):
    assert is_red_team(redteam_member.user)


def test_is_not_admin(superuser_member):
    assert not is_admin(superuser_member.user)


def test_is_admin(admin_member):
    assert is_admin(admin_member.user)


def test_indemnification_present(superuser_member):
    assert indemnification_present(superuser_member.user)


def test_can_scan_organization(superuser_member, organization):
    assert can_scan_organization(superuser_member.user, organization)
    assert superuser_member.delete()
    assert not can_scan_organization(superuser_member.user, organization)


def test_red_teamer_can_scan_organization(redteam_member, organization):
    assert can_scan_organization(redteam_member.user, organization)


def test_can_switch_organization(superuser_member):
    assert can_switch_organization(superuser_member.user)
