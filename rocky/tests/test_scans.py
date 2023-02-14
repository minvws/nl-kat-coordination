import json
from pathlib import Path

from pytest_django.asserts import assertContains, assertNotContains

from rocky.views.scans import ScanListView
from tests.conftest import setup_request


def test_katalogus_plugin_listing(my_user, rf, organization, mocker):
    mock_requests = mocker.patch("katalogus.client.requests")
    mock_response = mocker.MagicMock()
    mock_requests.get.return_value = mock_response
    mock_response.json.return_value = json.loads(
        (Path(__file__).parent / "stubs" / "katalogus_boefjes.json").read_text()
    )

    request = setup_request(rf.get("scan_list"), my_user)
    response = ScanListView.as_view()(request, organization_code=organization.code)

    assert response.status_code == 200
    assertContains(response, "Boefjes")
    assertContains(response, "BinaryEdge")
    assertNotContains(response, "test_binary_edge_normalizer")
