from pytest_django.asserts import assertContains

from rocky.views.ooi_edit import OOIEditView
from tests.conftest import setup_request


def test_ooi_edit(rf, my_user, organization, mock_organization_view_octopoes, network):
    mock_organization_view_octopoes().get.return_value = network

    request = setup_request(rf.get("ooi_edit", {"ooi_id": "Network|testnetwork"}), my_user)
    response = OOIEditView.as_view()(request, organization_code=organization.code)

    assert response.status_code == 200
    assertContains(response, "testnetwork")
    assertContains(response, "Save Network")
