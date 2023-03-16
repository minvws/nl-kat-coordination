import json
import uuid

from pytest_django.asserts import assertContains

from rocky.views.ooi_add import OOIAddView
from tests.conftest import setup_request


def test_add_ooi(rf, my_user, organization, mock_organization_view_octopoes, mock_bytes_client):
    request = setup_request(rf.post("ooi_add", {"ooi_type": "Network", "name": "testnetwork"}), my_user)

    response = OOIAddView.as_view()(request, organization_code=organization.code, ooi_type="Network")

    assert response.status_code == 302
    assert response.url == "/en/test/objects/detail/?ooi_id=Network%7Ctestnetwork"

    data_without_valid_time = (
        b'[{"ooi": {"object_type": "Network", "scan_profile": null,'
        b' "primary_key": "Network|testnetwork", "name": "testnetwork"}'
    )
    mock_bytes_client().add_manual_proof.assert_called_once()
    call_args = mock_bytes_client().add_manual_proof.call_args[0]

    assert isinstance(call_args[0], uuid.UUID)
    assert data_without_valid_time in call_args[1]
    assert json.loads(call_args[1].decode("utf-8"))

    assert mock_organization_view_octopoes().save_declaration.call_count == 1


def test_add_bad_schema(rf, my_user, organization, mock_organization_view_octopoes, mock_bytes_client):
    request = setup_request(rf.post("ooi_add", {"ooi_type": "Network", "testnamewrong": "testnetwork"}), my_user)

    response = OOIAddView.as_view()(request, organization_code=organization.code, ooi_type="Network")

    assert response.status_code == 200
    assertContains(response, "Error:")
    assertContains(response, "This field is required.")
