from pytest_django.asserts import assertContains

from openkat.views.ooi_add import OOIAddView
from tests.conftest import setup_request


def test_add_ooi(rf, client_member, octopoes_api_connector):
    request = setup_request(rf.post("ooi_add", {"ooi_type": "Network", "name": "testnetwork"}), client_member.user)

    response = OOIAddView.as_view()(request, organization_code=client_member.organization.code, ooi_type="Network")

    assert response.status_code == 302
    assert response.url == f"/en/{client_member.organization.code}/objects/detail/?ooi_id=Network%7Ctestnetwork"
    assert octopoes_api_connector.save_declaration.call_count == 1


def test_add_bad_schema(rf, client_member):
    request = setup_request(
        rf.post("ooi_add", {"ooi_type": "Network", "testnamewrong": "testnetwork"}), client_member.user
    )

    response = OOIAddView.as_view()(request, organization_code=client_member.organization.code, ooi_type="Network")

    assert response.status_code == 200
    assertContains(response, "Error:")
    assertContains(response, "This field is required.")
