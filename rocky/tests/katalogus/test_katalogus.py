import pytest
from django.core.exceptions import PermissionDenied
from katalogus.client import KATalogusClientV1, parse_plugin
from katalogus.views.katalogus import KATalogusView
from katalogus.views.katalogus_settings import ConfirmCloneSettingsView, KATalogusSettingsView
from katalogus.views.plugin_enable_disable import PluginEnableDisableView
from pytest_django.asserts import assertContains, assertNotContains

from rocky.health import ServiceHealth
from tests.conftest import create_member, get_boefjes_data, setup_request


def katalogus_plugin_listing(request, member, rf, mocker):
    mock_requests = mocker.patch("katalogus.client.requests")
    mock_response = mocker.MagicMock()
    mock_requests.Session().get.return_value = mock_response
    mock_response.json.return_value = get_boefjes_data()

    member = request.getfixturevalue(member)

    return KATalogusView.as_view()(
        setup_request(rf.get("katalogus"), member.user), organization_code=member.organization.code
    )


@pytest.mark.parametrize("member", ["superuser_member", "redteam_member"])
def test_katalogus_plugin_listing(request, member, rf, mocker):
    response = katalogus_plugin_listing(request, member, rf, mocker)

    assert response.status_code == 200

    assertNotContains(response, "You don't have permission to enable boefje")

    assertContains(response, "KAT-alogus")
    assertContains(response, "Enable")
    assertContains(response, "BinaryEdge")
    assertContains(response, "WPScantest")


@pytest.mark.parametrize("member", ["admin_member", "client_member"])
def test_katalogus_plugin_listing_no_perms(request, member, rf, mocker):
    response = katalogus_plugin_listing(request, member, rf, mocker)

    assert response.status_code == 200

    assertContains(response, "You don't have permission to enable boefje")

    assertNotContains(response, "KAT-alogus Settings")
    assertNotContains(response, "test_binary_edge_normalizer")


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


def test_katalogus_clone_settings_not_accessible_without_perms(
    client_member, organization_b, rf, mocker, mock_models_octopoes
):
    # Mock katalogus calls: return right boefjes and settings
    mocker.patch("katalogus.client.KATalogusClientV1")

    create_member(client_member.user, organization_b)

    request = setup_request(rf.post("confirm_clone_settings"), client_member.user)
    with pytest.raises(PermissionDenied):
        ConfirmCloneSettingsView.as_view()(
            request, organization_code=client_member.organization.code, to_organization=organization_b.code
        )


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


def test_enable_disable_plugin_no_clearance(rf, redteam_member, mocker):
    redteam_member.trusted_clearance_level = 1
    redteam_member.save()

    plugin = get_boefjes_data()[0]
    mock_requests = mocker.patch("katalogus.client.requests")
    mock_response = mocker.MagicMock()
    mock_requests.Session().get.return_value = mock_response
    mock_response.json.return_value = plugin

    request = setup_request(
        rf.post(
            "plugin_enable_disable",
        ),
        redteam_member.user,
    )

    response = PluginEnableDisableView.as_view()(
        setup_request(request, redteam_member.user),
        organization_code=redteam_member.organization.code,
        plugin_type=plugin["type"],
        plugin_id=plugin["id"],
        plugin_state=False,
    )

    # redirects back to KAT-alogus
    assert response.status_code == 302

    assert (
        list(request._messages).pop().message
        == "To enable "
        + plugin["name"].title()
        + " you need at least a clearance level of L"
        + str(plugin["scan_level"])
        + ". "
        "Your clearance level is L"
        + str(redteam_member.trusted_clearance_level)
        + ". Contact your administrator to get a higher clearance level."
    )


def test_enable_disable_plugin_no_clearance_other_text(rf, redteam_member, mocker):
    redteam_member.trusted_clearance_level = -1
    redteam_member.save()

    plugin = get_boefjes_data()[0]
    mock_requests = mocker.patch("katalogus.client.requests")
    mock_response = mocker.MagicMock()
    mock_requests.Session().get.return_value = mock_response
    mock_response.json.return_value = plugin

    request = setup_request(
        rf.post(
            "plugin_enable_disable",
        ),
        redteam_member.user,
    )

    response = PluginEnableDisableView.as_view()(
        setup_request(request, redteam_member.user),
        organization_code=redteam_member.organization.code,
        plugin_type=plugin["type"],
        plugin_id=plugin["id"],
        plugin_state=False,
    )

    # redirects back to KAT-alogus
    assert response.status_code == 302

    assert (
        list(request._messages).pop().message
        == "To enable "
        + plugin["name"].title()
        + " you need at least a clearance level of L"
        + str(plugin["scan_level"])
        + ". Your clearance level has not yet been set. Contact your administrator."
    )


def test_enable_disable_plugin_has_clearance(rf, redteam_member, mocker):
    plugin = get_boefjes_data()[0]
    mock_requests = mocker.patch("katalogus.client.requests")
    mock_response = mocker.MagicMock()
    mock_requests.Session().get.return_value = mock_response
    mock_response.json.return_value = plugin

    request = setup_request(
        rf.post(
            "plugin_enable_disable",
        ),
        redteam_member.user,
    )

    response = PluginEnableDisableView.as_view()(
        setup_request(request, redteam_member.user),
        organization_code=redteam_member.organization.code,
        plugin_type=plugin["type"],
        plugin_id=plugin["id"],
        plugin_state=False,
    )

    # redirects back to KAT-alogus
    assert response.status_code == 302

    assert list(request._messages).pop().message == "Boefje '" + plugin["name"] + "' enabled."
