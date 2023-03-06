import pytest
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from pytest_django.asserts import assertContains, assertNotContains

from rocky.views.organization_detail import OrganizationDetailView
from rocky.views.organization_edit import OrganizationEditView
from rocky.views.organization_list import OrganizationListView
from tests.conftest import setup_request
from tools.models import OrganizationMember


def test_organization_list_non_superuser(rf, my_user, organization, mock_models_katalogus, mock_models_octopoes):
    my_user.is_superuser = False
    my_user.user_permissions.add(Permission.objects.get(codename="view_organization"))

    request = setup_request(rf.get("organization_list"), my_user)
    response = OrganizationListView.as_view()(request)

    assertContains(response, "Organizations")
    assertNotContains(response, "Add new organization")
    assertContains(response, organization.name)


def test_edit_organization(rf, my_user, organization, mock_models_katalogus, mock_models_octopoes):
    request = setup_request(rf.get("organization_edit"), my_user)
    response = OrganizationEditView.as_view()(request, pk=organization.id)

    assert response.status_code == 200
    assertContains(response, "Name")
    assertContains(response, "Code")
    assertContains(response, organization.code)
    assertContains(response, organization.name)
    assertContains(response, "Save organization")


def test_organization_list(rf, my_user, organization, mock_models_katalogus, mock_models_octopoes):
    request = setup_request(rf.get("organization_list"), my_user)
    response = OrganizationListView.as_view()(request)

    assertContains(response, "Organizations")
    assertContains(response, "Add new organization")
    assertContains(response, organization.name)


def test_organization_member_list(rf, my_user, organization, mock_models_katalogus, mock_models_octopoes):
    request = setup_request(rf.get("organization_detail"), my_user)
    response = OrganizationDetailView.as_view()(request, organization_code=organization.code)

    assertContains(response, "Organization details")
    assertContains(response, organization.name)
    assertContains(response, "Members")
    assertContains(response, "Add new member")
    assertContains(response, my_user.email)
    assertContains(response, "Grant")


def test_organization_filtered_member_list(
    rf, my_user, my_new_user, my_blocked_user, organization, mock_models_katalogus, mock_models_octopoes
):
    request = setup_request(rf.get("organization_detail", {"client_status": "blocked"}), my_user)
    response = OrganizationDetailView.as_view()(request, organization_code=organization.code)

    assertNotContains(response, my_new_user.email)
    assertContains(response, my_blocked_user.email)
    assertContains(response, "Suspended")
    assertNotContains(response, "New")
    assertNotContains(response, "Active")

    request2 = setup_request(rf.get("organization_detail", {"client_status": "new"}), my_user)
    response2 = OrganizationDetailView.as_view()(request2, organization_code=organization.code)

    assertContains(response2, my_new_user.email)
    assertNotContains(response2, my_blocked_user.email)
    assertContains(response2, "New")
    assertNotContains(response2, "Suspended")
    assertNotContains(response2, "Active")

    request3 = setup_request(rf.get("organization_detail", {"client_status": ["new", "active", "blocked"]}), my_user)
    response3 = OrganizationDetailView.as_view()(request3, organization_code=organization.code)

    assertContains(response3, my_user.email)
    assertContains(response3, my_new_user.email)
    assertContains(response3, my_blocked_user.email)
    assertContains(response3, "New")
    assertContains(response3, "Suspended")
    assertContains(response3, "Active")


def test_organization_member_give_and_revoke_clearance(
    rf, my_user, organization, mock_models_katalogus, mock_models_octopoes
):
    member = OrganizationMember.objects.get(user=my_user)

    request = setup_request(
        rf.post(
            "organization_detail",
            {
                "action": "give_clearance",
                "member_id": member.id,
            },
        ),
        my_user,
    )
    response = OrganizationDetailView.as_view()(request, organization_code=organization.code)

    assert response.status_code == 302
    assert response.url == f"/en/{organization.code}/"

    request = setup_request(
        rf.post(
            "organization_detail",
            {
                "action": "withdraw_clearance",
                "member_id": member.id,
            },
        ),
        my_user,
    )
    response = OrganizationDetailView.as_view()(request, organization_code=organization.code)

    assert response.status_code == 302
    assert response.url == f"/en/{organization.code}/"

    request = setup_request(
        rf.post(
            "organization_detail",
            {
                "action": "wrong_test",
                "member_id": member.id,
            },
        ),
        my_user,
    )

    with pytest.raises(Exception) as exc_info:
        OrganizationDetailView.as_view()(request, organization_code=organization.code)

    assert exc_info.exconly() == "Exception: Unhandled allowed action: wrong_test"


def test_organization_member_give_and_revoke_clearance_no_action_reloads_page(
    rf, my_user, organization, mock_models_katalogus, mock_models_octopoes
):
    member = OrganizationMember.objects.get(user=my_user)

    # No action in the POST means we simply reload the page
    request = setup_request(
        rf.post(
            "organization_detail",
            {
                "wrong": "withdraw_clearance",
                "member_id": member.id,
            },
        ),
        my_user,
    )
    response = OrganizationDetailView.as_view()(request, organization_code=organization.code)
    assertContains(response, "Organization details")
    assertContains(response, organization.name)
    assertContains(response, "Members")
    assertContains(response, "Add new member")
    assertContains(response, my_user.email)
    assertContains(response, "Grant")


def test_organization_does_not_exist(client, normal_user, organization):
    client.force_login(normal_user)
    response = client.get(reverse("organization_detail", kwargs={"organization_code": "nonexistent"}))

    assert response.status_code == 404


def test_organization_no_member(client, normal_user_without_organization_member, organization):
    client.force_login(normal_user_without_organization_member)
    response = client.get(reverse("organization_detail", kwargs={"organization_code": organization.code}))

    assert response.status_code == 404


def test_organization_active_member(rf, normal_user, organization):
    request = setup_request(rf.get("organization_detail"), normal_user)
    response = OrganizationDetailView.as_view()(request, organization_code=organization.code)

    assert response.status_code == 200


def test_organization_blocked_member(rf, normal_user, organization):
    OrganizationMember.objects.filter(user=normal_user, organization=organization).update(status="blocked")

    request = setup_request(rf.get("organization_detail"), normal_user)
    with pytest.raises(PermissionDenied):
        OrganizationDetailView.as_view()(request, organization_code=organization.code)
