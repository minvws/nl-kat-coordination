import pytest
from django.core.exceptions import PermissionDenied
from pytest_django.asserts import assertContains

from openkat.views.ooi_delete import OOIDeleteView
from tests.conftest import setup_request


def test_ooi_delete(rf, redteam_member, octopoes_api_connector, network):
    octopoes_api_connector.get.return_value = network
    request = setup_request(rf.get("ooi_delete", {"ooi_id": "Network|testnetwork"}), redteam_member.user)
    response = OOIDeleteView.as_view()(request, organization_code=redteam_member.organization.code)

    assert response.status_code == 200
    assertContains(response, "testnetwork")
    assertContains(response, "Delete Network")
    assertContains(response, "Are you sure?")


def test_finding_delete(rf, redteam_member, octopoes_api_connector, finding):
    octopoes_api_connector.get.return_value = finding
    request = setup_request(rf.get("ooi_delete", {"ooi_id": finding.primary_key}), redteam_member.user)
    response = OOIDeleteView.as_view()(request, organization_code=redteam_member.organization.code)

    assert response.status_code == 200
    assertContains(response, "testnetwork")
    assertContains(response, "Delete Finding")
    assertContains(response, "Are you sure?")


@pytest.mark.parametrize("member", ["superuser_member", "admin_member", "redteam_member"])
def test_delete_ooi_perms(request, member, rf, octopoes_api_connector, network):
    member = request.getfixturevalue(member)
    octopoes_api_connector.get.return_value = network

    response = OOIDeleteView.as_view()(
        setup_request(rf.get("ooi_delete", {"ooi_id": "Network|testnetwork"}), member.user),
        organization_code=member.organization.code,
    )

    assert response.status_code == 200


def test_delete_ooi_perms_clients(rf, client_member, octopoes_api_connector, network):
    octopoes_api_connector.get.return_value = network

    with pytest.raises(PermissionDenied):
        OOIDeleteView.as_view()(
            setup_request(rf.get("ooi_delete", {"ooi_id": "Network|testnetwork"}), client_member.user),
            organization_code=client_member.organization.code,
        )
