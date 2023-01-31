from pytest_django.asserts import assertContains, assertNotContains

from katalogus.client import KATalogusClientV1, parse_plugin
from katalogus.views import KATalogusView, KATalogusSettingsListView, ConfirmCloneSettingsView
from rocky.health import ServiceHealth
from tests.conftest import setup_request, get_boefjes_data
from tools.models import Organization, OrganizationMember


def test_katalogus_plugin_listing(my_user, rf, organization, mocker):
    mock_requests = mocker.patch("katalogus.client.requests")
    mock_response = mocker.MagicMock()
    mock_requests.get.return_value = mock_response
    mock_response.json.return_value = get_boefjes_data()

    request = setup_request(rf.get("katalogus"), my_user)
    response = KATalogusView.as_view()(request, organization_code=organization.code)

    assertContains(response, "KAT-alogus")
    assertContains(response, "Settings")
    assertContains(response, "Enable")
    assertContains(response, "BinaryEdge")
    assertContains(response, "WPScantest")
    assertNotContains(response, "test_binary_edge_normalizer")


def test_katalogus_settings_list_one_organization(my_user, rf, organization, mocker):
    # Mock katalogus calls: return right boefjes and settings
    mock_katalogus = mocker.patch("katalogus.client.KATalogusClientV1")
    boefjes_data = get_boefjes_data()
    mock_katalogus().get_boefjes.return_value = [parse_plugin(b) for b in boefjes_data if b["type"] == "boefje"]
    mock_katalogus().get_plugin_settings.return_value = {"BINARYEDGE_API": "test"}

    request = setup_request(rf.get("katalogus_settings"), my_user)
    response = KATalogusSettingsListView.as_view()(request, organization_code=organization.code)
    assert response.status_code == 200

    assertContains(response, "KAT-alogus Settings")
    assertContains(response, "Plugin")
    assertContains(response, "Name")
    assertContains(response, "Value")
    assertContains(response, "BINARYEDGE_API")
    assertContains(response, "test")
    assertNotContains(response, "Clone settings")
    assertNotContains(response, "Organizations:")


def test_katalogus_settings_list_multiple_organization(my_user, rf, organization, mock_models_octopoes, mocker):
    # Mock katalogus calls: return right boefjes and settings
    mock_katalogus = mocker.patch("katalogus.client.KATalogusClientV1")
    boefjes_data = get_boefjes_data()
    mock_katalogus().get_boefjes.return_value = [parse_plugin(b) for b in boefjes_data if b["type"] == "boefje"]
    mock_katalogus().get_plugin_settings.return_value = {"BINARYEDGE_API": "test"}

    # Add another organization and organization member, since this view only shows for multiple organizations
    second_organization = Organization.objects.create(name="Second Test Organization", code="test2")
    OrganizationMember.objects.create(
        user=my_user,
        organization=second_organization,
        verified=True,
        authorized=True,
        status=OrganizationMember.STATUSES.ACTIVE,
        trusted_clearance_level=4,
        acknowledged_clearance_level=4,
    )

    request = setup_request(rf.get("katalogus_settings"), my_user)
    response = KATalogusSettingsListView.as_view()(request, organization_code=organization.code)
    assert response.status_code == 200

    assertContains(response, "KAT-alogus Settings")
    assertContains(response, "Plugin")
    assertContains(response, "Name")
    assertContains(response, "Value")
    assertContains(response, "BINARYEDGE_API")
    assertContains(response, "test")
    assertContains(response, "Clone settings")  # Now they appear
    assertContains(response, "Organizations:")  # Now they appear
    assertContains(response, second_organization.name)


def test_katalogus_confirm_clone_settings(my_user, rf, organization, mock_models_octopoes, mocker):
    mocker.patch("katalogus.client.KATalogusClientV1")

    # Add another organization and organization member, since this view only shows for multiple organizations
    second_organization = Organization.objects.create(name="Second Test Organization", code="test2")
    OrganizationMember.objects.create(
        user=my_user,
        organization=second_organization,
        verified=True,
        authorized=True,
        status=OrganizationMember.STATUSES.ACTIVE,
        trusted_clearance_level=4,
        acknowledged_clearance_level=4,
    )

    request = setup_request(rf.get("confirm_clone_settings"), my_user)
    response = ConfirmCloneSettingsView.as_view()(
        request, organization_code=organization.code, to_organization=second_organization.code
    )
    assert response.status_code == 200

    assertContains(response, "Clone settings")
    assertContains(response, "Be aware")
    assertContains(response, "Are you sure")
    assertContains(response, "Cancel")
    assertContains(response, "Clone")
    assertContains(response, organization.name)
    assertContains(response, second_organization.name)


def test_katalogus_clone_settings(my_user, rf, organization, mocker, mock_models_octopoes):
    # Mock katalogus calls: return right boefjes and settings
    mock_katalogus = mocker.patch("katalogus.client.KATalogusClientV1")

    # Add another organization and organization member, since this view only shows for multiple organizations
    second_organization = Organization.objects.create(name="Second Test Organization", code="test2")
    OrganizationMember.objects.create(
        user=my_user,
        organization=second_organization,
        verified=True,
        authorized=True,
        status=OrganizationMember.STATUSES.ACTIVE,
        trusted_clearance_level=4,
        acknowledged_clearance_level=4,
    )

    request = setup_request(rf.post("confirm_clone_settings"), my_user)
    response = ConfirmCloneSettingsView.as_view()(
        request, organization_code=organization.code, to_organization=second_organization.code
    )
    assert response.status_code == 302

    mock_katalogus().clone_all_configuration_to_organization.assert_called_once_with(second_organization.code)


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
