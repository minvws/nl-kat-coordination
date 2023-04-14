import pytest
from django.http import Http404
from pytest_django.asserts import assertContains, assertNotContains

from katalogus.views.plugin_settings_add import PluginSettingsAddView, PluginSingleSettingAddView
from tests.conftest import setup_request


def test_plugin_settings_add_view(
    rf,
    superuser_member,
    mock_mixins_katalogus,
    plugin_details,
    plugin_schema,
):
    mock_mixins_katalogus().get_plugin.return_value = plugin_details
    mock_mixins_katalogus().get_plugin_schema.return_value = plugin_schema

    request = setup_request(rf.post("plugin_settings_add", data={"boefje_id": 123}), superuser_member.user)
    response = PluginSettingsAddView.as_view()(
        request, organization_code=superuser_member.organization.code, plugin_type="boefje", plugin_id="test-plugin"
    )

    assertContains(response, "TestBoefje")
    assertContains(response, "Add setting")
    assertContains(response, "TEST_PROPERTY")
    assertContains(response, "TEST_PROPERTY2")
    assertContains(response, "Add settings and enable boefje")


def test_plugin_single_settings_add_view(
    rf,
    superuser_member,
    mock_mixins_katalogus,
    plugin_details,
    plugin_schema,
):
    mock_mixins_katalogus().get_plugin.return_value = plugin_details
    mock_mixins_katalogus().get_plugin_schema.return_value = plugin_schema

    request = setup_request(rf.post("plugin_settings_add", data={"boefje_id": 123}), superuser_member.user)
    response = PluginSingleSettingAddView.as_view()(
        request,
        organization_code=superuser_member.organization.code,
        plugin_type="boefje",
        plugin_id="test-plugin",
        setting_name="TEST_PROPERTY",
    )

    assertContains(response, "TEST_PROPERTY")
    assertNotContains(response, "TEST_PROPERTY2")


def test_plugin_single_settings_add_view_invalid_name(
    rf,
    superuser_member,
    mock_mixins_katalogus,
    plugin_details,
    plugin_schema,
):
    mock_mixins_katalogus().get_plugin.return_value = plugin_details
    mock_mixins_katalogus().get_plugin_schema.return_value = plugin_schema

    request = setup_request(rf.post("plugin_settings_add", data={"boefje_id": 123}), superuser_member.user)

    with pytest.raises(Http404):
        PluginSingleSettingAddView.as_view()(
            request,
            organization_code=superuser_member.organization.code,
            plugin_type="boefje",
            plugin_id="test-plugin",
            setting_name="BAD_PROPERTY",
        )


def test_plugin_single_settings_add_view_no_schema(
    rf,
    superuser_member,
    mock_mixins_katalogus,
    plugin_details,
):
    mock_mixins_katalogus().get_plugin.return_value = plugin_details
    mock_mixins_katalogus().get_plugin_schema.return_value = None

    request = setup_request(rf.post("plugin_settings_add", data={"boefje_id": 123}), superuser_member.user)
    with pytest.raises(Http404):
        PluginSingleSettingAddView.as_view()(
            request,
            organization_code=superuser_member.organization.code,
            plugin_type="boefje",
            plugin_id="test-plugin",
            setting_name="BAD_PROPERTY",
        )
