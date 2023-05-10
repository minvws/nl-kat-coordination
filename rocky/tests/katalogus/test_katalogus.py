import pytest
from katalogus.client import KATalogusClientV1, parse_plugin
from katalogus.views import ConfirmCloneSettingsView, KATalogusSettingsListView, KATalogusView
from pytest_django.asserts import assertContains, assertNotContains

from rocky.health import ServiceHealth
from tests.conftest import create_member, get_boefjes_data, setup_request


@pytest.mark.parametrize("member", ["superuser_member", "admin_member", "redteam_member", "client_member"])
def test_katalogus_plugin_listing(request, member, rf, mocker):
    mock_requests = mocker.patch("katalogus.client.requests")
    mock_response = mocker.MagicMock()
    mock_requests.Session().get.return_value = mock_response
    mock_response.json.return_value = get_boefjes_data()

    member = request.getfixturevalue(member)

    response = KATalogusView.as_view()(
        setup_request(rf.get("katalogus"), member.user), organization_code=member.organization.code
    )

    assert response.status_code == 200

    assertContains(response, "KAT-alogus")
    assertContains(response, "Enable")
    assertContains(response, "BinaryEdge")
    assertContains(response, "WPScantest")


@pytest.mark.parametrize("member", ["admin_member", "client_member"])
def test_katalogus_plugin_listing(request, member, rf, mocker):
    mock_requests = mocker.patch("katalogus.client.requests")
    mock_response = mocker.MagicMock()
    mock_requests.Session().get.return_value = mock_response
    mock_response.json.return_value = get_boefjes_data()

    member = request.getfixturevalue(member)

    response = KATalogusView.as_view()(
        setup_request(rf.get("katalogus"), member.user), organization_code=member.organization.code
    )

    assertContains(response, "You don't have permission to enable boefje")

    assertNotContains(response, "KAT-alogus Settings")
    assertNotContains(response, "test_binary_edge_normalizer")


def test_katalogus_settings_list_one_organization(redteam_member, rf, mocker):
    # Mock katalogus calls: return right boefjes and settings
    mock_katalogus = mocker.patch("katalogus.client.KATalogusClientV1")
    boefjes_data = get_boefjes_data()
    mock_katalogus().get_boefjes.return_value = [parse_plugin(b) for b in boefjes_data if b["type"] == "boefje"]
    mock_katalogus().get_plugin_settings.return_value = {"BINARYEDGE_API": "test"}

    request = setup_request(rf.get("katalogus_settings"), redteam_member.user)
    response = KATalogusSettingsListView.as_view()(request, organization_code=redteam_member.organization.code)
    assert response.status_code == 200

    assertContains(response, "KAT-alogus Settings")
    assertContains(response, "Plugin")
    assertContains(response, "Name")
    assertContains(response, "Value")
    assertContains(response, "BINARYEDGE_API")
    assertContains(response, "test")
    assertNotContains(response, "Clone settings")
    assertNotContains(response, "Organizations:")


def test_katalogus_settings_list_multiple_organization(redteam_member, organization_b, rf, mocker):
    # Mock katalogus calls: return right boefjes and settings
    mock_katalogus = mocker.patch("katalogus.client.KATalogusClientV1")
    boefjes_data = get_boefjes_data()
    mock_katalogus().get_boefjes.return_value = [parse_plugin(b) for b in boefjes_data if b["type"] == "boefje"]
    mock_katalogus().get_plugin_settings.return_value = {"BINARYEDGE_API": "test"}

    create_member(redteam_member.user, organization_b)

    request = setup_request(rf.get("katalogus_settings"), redteam_member.user)
    response = KATalogusSettingsListView.as_view()(request, organization_code=redteam_member.organization.code)
    assert response.status_code == 200

    assertContains(response, "KAT-alogus Settings")
    assertContains(response, "Plugin")
    assertContains(response, "Name")
    assertContains(response, "Value")
    assertContains(response, "BINARYEDGE_API")
    assertContains(response, "test")

    assertContains(response, "Clone settings")  # Now they appear
    assertContains(response, "Organizations:")  # Now they appear
    assertContains(response, organization_b.name)


def test_katalogus_confirm_clone_settings(redteam_member, organization_b, rf, mock_models_octopoes, mocker):
    mocker.patch("katalogus.client.KATalogusClientV1")

    create_member(redteam_member.user, organization_b)

    request = setup_request(rf.get("confirm_clone_settings"), redteam_member.user)
    response = ConfirmCloneSettingsView.as_view()(
        request, organization_code=redteam_member.organization.code, to_organization=organization_b.code
    )
    assert response.status_code == 200

    assertContains(response, "Clone settings")
    assertContains(response, "Be aware")
    assertContains(response, "Are you sure")
    assertContains(response, "Cancel")
    assertContains(response, "Clone")
    assertContains(response, redteam_member.organization.name)
    assertContains(response, organization_b.name)


def test_katalogus_clone_settings(redteam_member, organization_b, rf, mocker, mock_models_octopoes):
    # Mock katalogus calls: return right boefjes and settings
    mock_katalogus = mocker.patch("katalogus.client.KATalogusClientV1")

    create_member(redteam_member.user, organization_b)

    request = setup_request(rf.post("confirm_clone_settings"), redteam_member.user)
    response = ConfirmCloneSettingsView.as_view()(
        request, organization_code=redteam_member.organization.code, to_organization=organization_b.code
    )
    assert response.status_code == 302

    mock_katalogus().clone_all_configuration_to_organization.assert_called_once_with(organization_b.code)


def test_katalogus_client_organization_not_exists(mocker):
    mock_requests = mocker.patch("katalogus.client.requests")
    mock_requests.Session().get().status_code = 404

    client = KATalogusClientV1("test", "test")

    assert client.organization_exists() is False


def test_katalogus_client_organization_exists(mocker):
    mock_requests = mocker.patch("katalogus.client.requests")
    mock_requests.Session().get().status_code = 200

    client = KATalogusClientV1("test", "test")

    assert client.organization_exists() is True


def test_katalogus_client(mocker):
    mock_requests = mocker.patch("katalogus.client.requests")

    mock_response = mocker.MagicMock()
    mock_requests.Session().get.return_value = mock_response
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
