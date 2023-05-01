import pytest
from django.core.exceptions import PermissionDenied
from pytest_django.asserts import assertContains

from rocky.views.ooi_delete import OOIDeleteView
from tests.conftest import setup_request


def test_ooi_delete(rf, redteam_member, mock_organization_view_octopoes, network):
    mock_organization_view_octopoes().get.return_value = network
    request = setup_request(rf.get("ooi_delete", {"ooi_id": "Network|testnetwork"}), redteam_member.user)
    response = OOIDeleteView.as_view()(request, organization_code=redteam_member.organization.code)

    assert response.status_code == 200
    assertContains(response, "testnetwork")
    assertContains(response, "Delete Network")
    assertContains(response, "Are you sure?")


def test_finding_delete(rf, redteam_member, mock_organization_view_octopoes, finding):
    mock_organization_view_octopoes().get.return_value = finding
    request = setup_request(rf.get("ooi_delete", {"ooi_id": finding.primary_key}), redteam_member.user)
    response = OOIDeleteView.as_view()(request, organization_code=redteam_member.organization.code)

    assert response.status_code == 200
    assertContains(response, "testnetwork")
    assertContains(response, "Delete Finding")
    assertContains(response, "Are you sure?")


def test_delete_ooi_perms(
    rf, superuser_member, admin_member, redteam_member, client_member, mock_organization_view_octopoes, network
):
    mock_organization_view_octopoes().get.return_value = network

    response_superuser = OOIDeleteView.as_view()(
        setup_request(rf.get("ooi_delete", {"ooi_id": "Network|testnetwork"}), superuser_member.user),
        organization_code=superuser_member.organization.code,
    )
    response_admin = OOIDeleteView.as_view()(
        setup_request(rf.get("ooi_delete", {"ooi_id": "Network|testnetwork"}), admin_member.user),
        organization_code=admin_member.organization.code,
    )
    response_redteam = OOIDeleteView.as_view()(
        setup_request(rf.get("ooi_delete", {"ooi_id": "Network|testnetwork"}), redteam_member.user),
        organization_code=redteam_member.organization.code,
    )

    assert response_superuser.status_code == 200
    assert response_admin.status_code == 200
    assert response_redteam.status_code == 200

    with pytest.raises(PermissionDenied):
        OOIDeleteView.as_view()(
            setup_request(rf.get("ooi_delete", {"ooi_id": "Network|testnetwork"}), client_member.user),
            organization_code=client_member.organization.code,
        )
