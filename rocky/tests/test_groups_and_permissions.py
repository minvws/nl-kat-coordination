def test_is_not_red_team(superuser_member):
    assert not superuser_member.is_redteam


def test_is_red_team(redteam_member):
    assert redteam_member.is_redteam


def test_is_not_admin(superuser_member):
    assert not superuser_member.is_admin


def test_is_admin(admin_member):
    assert admin_member.is_admin


def test_indemnification_present(superuser_member):
    assert superuser_member.user.indemnification_set.exists()


def test_red_teamer_can_scan_organization(redteam_member):
    assert redteam_member.user.has_perm("can_scan_organization") or redteam_member.has_member_perm(
        "can_scan_organization"
    )
