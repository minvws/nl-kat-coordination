import pytest
from django.http import Http404
from pytest_django.asserts import assertContains, assertNotContains

from katalogus.views.plugin_settings_delete import PluginSettingsDeleteView
from tests.conftest import setup_request


def test_plugin_settings_delete_view(
    rf,
    my_user,
    organization,
    mock_mixins_katalogus,
    plugin_details,
    plugin_schema,
):
    mock_mixins_katalogus().get_plugin.return_value = plugin_details
    mock_mixins_katalogus().get_plugin_schema.return_value = plugin_schema

    request = setup_request(rf.get("plugin_settings_delete", data={"boefje_id": 123}), my_user)
    response = PluginSettingsDeleteView.as_view()(
        request,
        organization_code=organization.code,
        plugin_type="boefje",
        plugin_id="test-plugin",
        setting_name="TEST_PROPERTY",
    )

    assertContains(response, "TestBoefje")
    assertContains(response, "Delete setting")
    assertContains(response, "TEST_PROPERTY")
    assertNotContains(response, "TEST_PROPERTY2")


def test_plugin_settings_delete_view_invalid_setting_name(
    rf,
    my_user,
    organization,
    mock_mixins_katalogus,
    plugin_details,
    plugin_schema,
):
    mock_mixins_katalogus().get_plugin.return_value = plugin_details
    mock_mixins_katalogus().get_plugin_schema.return_value = plugin_schema

    request = setup_request(rf.get("plugin_settings_delete", data={"boefje_id": 123}), my_user)
    with pytest.raises(Http404):
        PluginSettingsDeleteView.as_view()(
            request,
            organization_code=organization.code,
            plugin_type="boefje",
            plugin_id="test-plugin",
            setting_name="BAD_PROPERTY",
        )
