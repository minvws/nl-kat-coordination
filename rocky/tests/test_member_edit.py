import pytest
from pytest_django.asserts import assertContains
from django.http import Http404
from django.core.exceptions import PermissionDenied
from tests.conftest import setup_request
from rocky.views.organization_member_edit import OrganizationMemberEditView
from tests.setup import UserSetup, OrganizationSetup, MemberSetup


def test_admin_can_edit_itself(rf, admin_member, organization):
    """
    This will test if an admin member can edit itself.
    """

    request = setup_request(rf.get("organization_member_edit"), admin_member.user)
    response = OrganizationMemberEditView.as_view()(request, organization_code=organization.code, pk=admin_member.id)
    assert response.status_code == 200
    assertContains(response, "Edit member")


def test_superuser_can_edit_itself(rf, superuser_member, organization):
    """
    This will test if a superuser can edit itself.
    """

    request = setup_request(rf.get("organization_member_edit"), superuser_member.user)
    response = OrganizationMemberEditView.as_view()(
        request, organization_code=organization.code, pk=superuser_member.id
    )
    assert response.status_code == 200
    assertContains(response, "Edit member")


def test_client_can_edit_itself(rf, client_member, organization):
    """
    This will test if a client member can edit itself. Only admins and superusers have edit rights.
    """

    request = setup_request(rf.get("organization_member_edit"), client_member.user)
    with pytest.raises(PermissionDenied):
        OrganizationMemberEditView.as_view()(request, organization_code=organization.code, pk=client_member.id)


def test_redteam_can_edit_itself(rf, redteam_member, organization):
    """
    This will test if a redteam member can edit itself. Only admins and supersuers have edit rights.
    """

    request = setup_request(rf.get("organization_member_edit"), redteam_member.user)
    with pytest.raises(PermissionDenied):
        OrganizationMemberEditView.as_view()(request, organization_code=organization.code, pk=redteam_member.id)


def test_admin_can_edit_superuser(rf, admin_member, superuser_member, organization):
    """
    This will test if admin can edit superuser at the member edit view.
    """

    request = setup_request(rf.get("organization_member_edit"), admin_member.user)
    with pytest.raises(PermissionDenied):
        OrganizationMemberEditView.as_view()(request, organization_code=organization.code, pk=superuser_member.id)


def test_client_can_edit_superuser(rf, client_member, superuser_member, organization):
    """
    This will test if client can edit superuser at the member edit view.
    """

    request = setup_request(rf.get("organization_member_edit"), client_member.user)
    with pytest.raises(PermissionDenied):
        OrganizationMemberEditView.as_view()(request, organization_code=organization.code, pk=superuser_member.id)


def test_redteamer_can_edit_superuser(rf, redteam_member, superuser_member, organization):
    """
    This will test if redteamer can edit superuser at the member edit view.
    """

    request = setup_request(rf.get("organization_member_edit"), redteam_member.user)
    with pytest.raises(PermissionDenied):
        OrganizationMemberEditView.as_view()(request, organization_code=organization.code, pk=superuser_member.id)


def test_edit_superusers_from_different_organizations(rf, django_user_model, superuser_member):
    """
    This will test if a superuser from one organization can edit
    a superuser from another organization at the member edit view.
    """
    organization_b = OrganizationSetup("OrganizationB", "org_b").create_organization()
    superuser_b = UserSetup(django_user_model)._create_superuser(
        email="superuserB@openkat.nl", password="SuperBSuperB123!!"
    )
    superuser_member_b = MemberSetup(superuser_b, organization_b).create_member()
    request = setup_request(rf.get("organization_member_edit"), superuser_member.user)
    # from OrganizationView
    with pytest.raises(Http404):
        OrganizationMemberEditView.as_view()(request, organization_code=organization_b.code, pk=superuser_member_b.id)
