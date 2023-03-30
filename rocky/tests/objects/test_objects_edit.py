from pytest_django.asserts import assertContains

from rocky.views.ooi_edit import OOIEditView
from tests.conftest import setup_request


def test_ooi_edit(rf, client_member, mock_organization_view_octopoes, network):
    mock_organization_view_octopoes().get.return_value = network

    request = setup_request(rf.get("ooi_edit", {"ooi_id": "Network|testnetwork"}), client_member.user)
    response = OOIEditView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 200
    assertContains(response, "testnetwork")
    assertContains(response, "Save Network")
