import json
from pathlib import Path

from pytest_django.asserts import assertContains, assertNotContains

from katalogus.client import KATalogusClientV1
from katalogus.views import KATalogusView
from rocky.health import ServiceHealth
from tests.conftest import setup_request


def test_katalogus_plugin_listing(my_user, rf, organization, mocker):
    mock_requests = mocker.patch("katalogus.client.requests")
    mock_response = mocker.MagicMock()
    mock_requests.get.return_value = mock_response
    mock_response.json.return_value = json.loads(
        (Path(__file__).parent / "stubs" / "katalogus_boefjes.json").read_text()
    )

    request = setup_request(rf.get("katalogus"), my_user)
    response = KATalogusView.as_view()(request, organization_code=organization.code)

    assertContains(response, "KAT-alogus")
    assertContains(response, "Enable")
    assertContains(response, "BinaryEdge")
    assertContains(response, "WPScantest")
    assertNotContains(response, "test_binary_edge_normalizer")


def test_katalogus_client_organization_not_exists(mocker):
    mock_requests = mocker.patch("katalogus.client.requests")
    mock_requests.get().status_code = 404

    client = KATalogusClientV1("test", "test")

    assert client.organization_exists() is False


def test_katalogus_client_organization_exists(mocker):
    mock_requests = mocker.patch("katalogus.client.requests")
    mock_requests.get().status_code = 200

    client = KATalogusClientV1("test", "test")

    assert client.organization_exists() is True


def test_katalogus_client(mocker):
    mock_requests = mocker.patch("katalogus.client.requests")

    mock_response = mocker.MagicMock()
    mock_requests.get.return_value = mock_response
    mock_response.json.return_value = {
        "service": "test",
        "healthy": False,
        "version": None,
        "additional": 2,
        "results": [],
    }

    client = KATalogusClientV1("test", "test")

    assert isinstance(client.health(), ServiceHealth)
    assert client.health().service == "test"
    assert not client.health().healthy
    assert client.health().additional == 2
    assert client.health().results == []
