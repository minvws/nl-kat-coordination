from pytest_django.asserts import assertContains

from rocky.views.ooi_delete import OOIDeleteView
from tests.conftest import setup_request


def test_ooi_delete(rf, client_member, mock_organization_view_octopoes, network):
    mock_organization_view_octopoes().get.return_value = network
    request = setup_request(rf.get("ooi_delete", {"ooi_id": "Network|testnetwork"}), client_member.user)
    response = OOIDeleteView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 200
    assertContains(response, "testnetwork")
    assertContains(response, "Delete Network")
    assertContains(response, "Are you sure?")


def test_finding_delete(rf, client_member, mock_organization_view_octopoes, finding):
    mock_organization_view_octopoes().get.return_value = finding
    request = setup_request(rf.get("ooi_delete", {"ooi_id": finding.primary_key}), client_member.user)
    response = OOIDeleteView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 200
    assertContains(response, "testnetwork")
    assertContains(response, "Delete Finding")
    assertContains(response, "Are you sure?")
