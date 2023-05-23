from katalogus.client import KATalogusClientV1, parse_plugin
from katalogus.views import ConfirmCloneSettingsView, KATalogusSettingsView, KATalogusView
from pytest_django.asserts import assertContains, assertNotContains

from rocky.health import ServiceHealth
from tests.conftest import create_member, get_boefjes_data, setup_request


def test_katalogus_plugin_listing(admin_member, redteam_member, client_member, rf, mocker):
    mock_requests = mocker.patch("katalogus.client.requests")
    mock_response = mocker.MagicMock()
    mock_requests.Session().get.return_value = mock_response
    mock_response.json.return_value = get_boefjes_data()

    request_admin = setup_request(rf.get("katalogus"), admin_member.user)
    response_admin = KATalogusView.as_view()(request_admin, organization_code=admin_member.organization.code)

    request_redteam = setup_request(rf.get("katalogus"), redteam_member.user)
    response_redteam = KATalogusView.as_view()(request_redteam, organization_code=redteam_member.organization.code)

    request_client = setup_request(rf.get("katalogus"), client_member.user)
    response_client = KATalogusView.as_view()(request_client, organization_code=client_member.organization.code)

    assertContains(response_client, "KAT-alogus")

    assertNotContains(response_redteam, "You don't have permission to enable boefje")
    assertContains(response_admin, "You don't have permission to enable boefje")
    assertContains(response_client, "You don't have permission to enable boefje")

    assertContains(response_redteam, "KAT-alogus Settings")
    assertNotContains(response_client, "KAT-alogus Settings")
    assertNotContains(response_admin, "KAT-alogus Settings")

    assertContains(response_client, "Enable")
    assertContains(response_client, "BinaryEdge")
    assertContains(response_client, "WPScantest")
    assertNotContains(response_client, "test_binary_edge_normalizer")


def test_katalogus_settings_one_organization(redteam_member, rf, mocker):
    # Mock katalogus calls: return right boefjes and settings
    mock_katalogus = mocker.patch("katalogus.client.KATalogusClientV1")
    boefjes_data = get_boefjes_data()
    mock_katalogus().get_boefjes.return_value = [parse_plugin(b) for b in boefjes_data if b["type"] == "boefje"]
    mock_katalogus().get_plugin_settings.return_value = {"BINARYEDGE_API": "test", "Second": "value"}

    request = setup_request(rf.get("katalogus_settings"), redteam_member.user)
    response = KATalogusSettingsView.as_view()(request, organization_code=redteam_member.organization.code)
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
    response = KATalogusSettingsView.as_view()(request, organization_code=redteam_member.organization.code)
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


def test_katalogus_confirm_clone_settings(client_member, organization_b, rf, mock_models_octopoes, mocker):
    mocker.patch("katalogus.client.KATalogusClientV1")

    create_member(client_member.user, organization_b)

    request = setup_request(rf.get("confirm_clone_settings"), client_member.user)
    response = ConfirmCloneSettingsView.as_view()(
        request, organization_code=client_member.organization.code, to_organization=organization_b.code
    )
    assert response.status_code == 200

    assertContains(response, "Clone settings")
    assertContains(response, "Be aware")
    assertContains(response, "Are you sure")
    assertContains(response, "Cancel")
    assertContains(response, "Clone")
    assertContains(response, client_member.organization.name)
    assertContains(response, organization_b.name)


def test_katalogus_clone_settings(client_member, organization_b, rf, mocker, mock_models_octopoes):
    # Mock katalogus calls: return right boefjes and settings
    mock_katalogus = mocker.patch("katalogus.client.KATalogusClientV1")

    create_member(client_member.user, organization_b)

    request = setup_request(rf.post("confirm_clone_settings"), client_member.user)
    response = ConfirmCloneSettingsView.as_view()(
        request, organization_code=client_member.organization.code, to_organization=organization_b.code
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
