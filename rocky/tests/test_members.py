import pytest
from django.core.exceptions import PermissionDenied
from django.http import Http404
from pytest_django.asserts import assertContains

from rocky.views.organization_member_edit import OrganizationMemberEditView
from tests.conftest import setup_request


def test_admin_can_edit_itself(rf, admin_member):
    """
    This will test if an admin member can edit itself.
    """

    request = setup_request(rf.get("organization_member_edit"), admin_member.user)
    response = OrganizationMemberEditView.as_view()(
        request, organization_code=admin_member.organization.code, pk=admin_member.id
    )
    assert response.status_code == 200
    assertContains(response, "Edit member")


def test_superuser_can_edit_itself(rf, superuser_member):
    """
    This will test if a superuser can edit itself.
    """

    request = setup_request(rf.get("organization_member_edit"), superuser_member.user)
    response = OrganizationMemberEditView.as_view()(
        request, organization_code=superuser_member.organization.code, pk=superuser_member.id
    )
    assert response.status_code == 200
    assertContains(response, "Edit member")


def test_client_can_edit_itself(rf, client_member):
    """
    This will test if a client member can edit itself. Only admins and superusers have edit rights.
    """

    request = setup_request(rf.get("organization_member_edit"), client_member.user)
    with pytest.raises(PermissionDenied):
        OrganizationMemberEditView.as_view()(
            request, organization_code=client_member.organization.code, pk=client_member.id
        )


def test_redteam_can_edit_itself(rf, redteam_member):
    """
    This will test if a redteam member can edit itself. Only admins and supersuers have edit rights.
    """

    request = setup_request(rf.get("organization_member_edit"), redteam_member.user)
    with pytest.raises(PermissionDenied):
        OrganizationMemberEditView.as_view()(
            request, organization_code=redteam_member.organization.code, pk=redteam_member.id
        )


def test_admin_can_edit_superuser(rf, admin_member, superuser_member):
    """
    This will test if admin can edit superuser at the member edit view.
    """

    request = setup_request(rf.get("organization_member_edit"), admin_member.user)
    with pytest.raises(PermissionDenied):
        OrganizationMemberEditView.as_view()(
            request, organization_code=superuser_member.organization.code, pk=superuser_member.id
        )


def test_client_can_edit_superuser(rf, client_member, superuser_member):
    """
    This will test if client can edit superuser at the member edit view.
    """

    request = setup_request(rf.get("organization_member_edit"), client_member.user)
    with pytest.raises(PermissionDenied):
        OrganizationMemberEditView.as_view()(
            request, organization_code=superuser_member.organization.code, pk=superuser_member.id
        )


def test_redteamer_can_edit_superuser(rf, redteam_member, superuser_member, organization):
    """
    This will test if redteamer can edit superuser at the member edit view.
    """

    request = setup_request(rf.get("organization_member_edit"), redteam_member.user)
    with pytest.raises(PermissionDenied):
        OrganizationMemberEditView.as_view()(request, organization_code=organization.code, pk=superuser_member.id)


def test_edit_superusers_from_different_organizations(rf, superuser_member, superuser_member_b):
    """
    This will test if a superuser from one organization can edit
    a superuser from another organization at the member edit view.
    """

    request = setup_request(rf.get("organization_member_edit"), superuser_member.user)
    # from OrganizationView
    with pytest.raises(Http404):
        OrganizationMemberEditView.as_view()(
            request, organization_code=superuser_member_b.organization.code, pk=superuser_member_b.id
        )


def test_edit_admins_from_different_organizations(rf, admin_member, admin_member_b):
    """
    This will test if a admin from one organization can edit
    an admin from another organization at the member edit view.
    """

    request = setup_request(rf.get("organization_member_edit"), admin_member.user)
    # from OrganizationView
    with pytest.raises(Http404):
        OrganizationMemberEditView.as_view()(
            request, organization_code=admin_member_b.organization.code, pk=admin_member_b.id
        )


def test_admin_edits_client_different_orgs(rf, admin_member, client_member_b):
    request = setup_request(
        rf.post(
            "organization_member_edit",
            {"status": "blocked", "trusted_clearance_level": 4},
        ),
        admin_member.user,
    )
    with pytest.raises(Http404):
        OrganizationMemberEditView.as_view()(
            request, organization_code=client_member_b.organization.code, pk=client_member_b.id
        )


def test_admin_edits_redteamer(rf, admin_member, redteam_member):
    request = setup_request(
        rf.post(
            "organization_member_edit",
            {"status": "active", "trusted_clearance_level": 4},
        ),
        admin_member.user,
    )
    OrganizationMemberEditView.as_view()(
        request, organization_code=redteam_member.organization.code, pk=redteam_member.id
    )

    redteam_member.refresh_from_db()
    assert redteam_member.status == "active"
    assert redteam_member.trusted_clearance_level == 4


def test_admin_edits_redteamer_to_block(rf, admin_member, redteam_member):
    request = setup_request(
        rf.post(
            "organization_member_edit",
            {"status": "blocked", "trusted_clearance_level": 4},
        ),
        admin_member.user,
    )
    OrganizationMemberEditView.as_view()(
        request, organization_code=redteam_member.organization.code, pk=redteam_member.id
    )

    redteam_member.refresh_from_db()
    assert redteam_member.status == "blocked"
