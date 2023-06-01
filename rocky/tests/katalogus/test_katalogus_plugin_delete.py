from django.urls import reverse
from katalogus.views.plugin_settings_delete import PluginSettingsDeleteView
from pytest_django.asserts import assertContains
from requests import RequestException

from tests.conftest import setup_request


def test_plugin_settings_delete_view(
    rf,
    superuser_member,
    mock_mixins_katalogus,
    plugin_details,
    plugin_schema,
):
    mock_mixins_katalogus().get_plugin.return_value = plugin_details
    mock_mixins_katalogus().get_plugin_schema.return_value = plugin_schema

    request = setup_request(rf.get("plugin_settings_delete"), superuser_member.user)
    response = PluginSettingsDeleteView.as_view()(
        request,
        organization_code=superuser_member.organization.code,
        plugin_type="boefje",
        plugin_id="test-plugin",
        setting_name="TEST_PROPERTY",
    )

    assertContains(response, "TestBoefje")
    assertContains(response, "Delete settings")


def test_plugin_settings_delete(
    rf,
    superuser_member,
    mock_mixins_katalogus,
    plugin_details,
    plugin_schema,
):
    mock_katalogus = mock_mixins_katalogus()
    mock_katalogus.get_plugin.return_value = plugin_details
    mock_katalogus.get_plugin_schema.return_value = plugin_schema

    request = setup_request(rf.post("plugin_settings_delete"), superuser_member.user)
    response = PluginSettingsDeleteView.as_view()(
        request,
        organization_code=superuser_member.organization.code,
        plugin_type="boefje",
        plugin_id="test-boefje",
    )

    assert response.status_code == 302
    assert response.headers["Location"] == reverse(
        "plugin_detail",
        kwargs={
            "organization_code": superuser_member.organization.code,
            "plugin_type": "boefje",
            "plugin_id": "test-boefje",
        },
    )
    assert list(request._messages).pop().message == "Settings for plugin TestBoefje successfully deleted."


def test_plugin_settings_delete_failed(
    rf,
    mocker,
    superuser_member,
    mock_mixins_katalogus,
    plugin_details,
    plugin_schema,
):
    mock_katalogus = mock_mixins_katalogus()
    mock_katalogus.get_plugin.return_value = plugin_details
    mock_katalogus.get_plugin_schema.return_value = plugin_schema
    mock_katalogus.delete_plugin_settings.side_effect = RequestException(response=mocker.MagicMock(status_code=500))

    request = setup_request(rf.post("plugin_settings_delete"), superuser_member.user)
    response = PluginSettingsDeleteView.as_view()(
        request,
        organization_code=superuser_member.organization.code,
        plugin_type="boefje",
        plugin_id="test-boefje",
    )

    assert response.status_code == 302
    assert response.headers["Location"] == reverse(
        "plugin_detail",
        kwargs={
            "organization_code": superuser_member.organization.code,
            "plugin_type": "boefje",
            "plugin_id": "test-boefje",
        },
    )
    assert (
        list(request._messages).pop().message
        == "Failed deleting Settings for plugin TestBoefje. Check the Katalogus logs for more info."
    )


def test_plugin_settings_delete_no_settings_present(
    rf,
    mocker,
    superuser_member,
    mock_mixins_katalogus,
    plugin_details,
    plugin_schema,
):
    mock_katalogus = mock_mixins_katalogus()
    mock_katalogus.get_plugin.return_value = plugin_details
    mock_katalogus.get_plugin_schema.return_value = plugin_schema
    mock_katalogus.delete_plugin_settings.side_effect = RequestException(response=mocker.MagicMock(status_code=404))

    request = setup_request(rf.post("plugin_settings_delete"), superuser_member.user)
    response = PluginSettingsDeleteView.as_view()(
        request,
        organization_code=superuser_member.organization.code,
        plugin_type="boefje",
        plugin_id="test-boefje",
    )

    assert response.status_code == 302
    assert response.headers["Location"] == reverse(
        "plugin_detail",
        kwargs={
            "organization_code": superuser_member.organization.code,
            "plugin_type": "boefje",
            "plugin_id": "test-boefje",
        },
    )
    assert list(request._messages).pop().message == "Plugin TestBoefje has no settings."
