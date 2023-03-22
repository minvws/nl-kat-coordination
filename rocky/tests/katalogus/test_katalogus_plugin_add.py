from pytest_django.asserts import assertContains, assertNotContains

from katalogus.views.plugin_settings_add import PluginSettingsAddView, PluginSingleSettingAddView
from tests.conftest import setup_request


def test_plugin_settings_add_view(
    rf,
    my_user,
    organization,
    mock_mixins_katalogus,
    plugin_details,
    plugin_schema,
    mock_organization_view_octopoes,
):
    mock_mixins_katalogus().get_plugin.return_value = plugin_details
    mock_mixins_katalogus().get_plugin_schema.return_value = plugin_schema

    request = setup_request(rf.post("step_organization_setup", data={"boefje_id": 123}), my_user)
    response = PluginSettingsAddView.as_view()(
        request, organization_code=organization.code, plugin_type="boefje", plugin_id="test-plugin"
    )

    assertContains(response, "TestBoefje")
    assertContains(response, "Add setting")
    assertContains(response, "TEST_PROPERTY")
    assertContains(response, "TEST_PROPERTY2")
    assertContains(response, "Add settings and enable boefje")


def test_plugin_single_settings_add_view(
    rf,
    my_user,
    organization,
    mock_mixins_katalogus,
    plugin_details,
    plugin_schema,
    mock_organization_view_octopoes,
):
    mock_mixins_katalogus().get_plugin.return_value = plugin_details
    mock_mixins_katalogus().get_plugin_schema.return_value = plugin_schema

    request = setup_request(rf.post("step_organization_setup", data={"boefje_id": 123}), my_user)
    response = PluginSingleSettingAddView.as_view()(
        request,
        organization_code=organization.code,
        plugin_type="boefje",
        plugin_id="test-plugin",
        setting_name="TEST_PROPERTY",
    )

    assertContains(response, "TEST_PROPERTY")
    assertNotContains(response, "TEST_PROPERTY2")


def test_plugin_single_settings_add_view_invalid_name(
    rf,
    my_user,
    organization,
    mock_mixins_katalogus,
    plugin_details,
    plugin_schema,
    mock_organization_view_octopoes,
):
    mock_mixins_katalogus().get_plugin.return_value = plugin_details
    mock_mixins_katalogus().get_plugin_schema.return_value = plugin_schema

    request = setup_request(rf.post("step_organization_setup", data={"boefje_id": 123}), my_user)
    response = PluginSingleSettingAddView.as_view()(
        request,
        organization_code=organization.code,
        plugin_type="boefje",
        plugin_id="test-plugin",
        setting_name="BAD_PROPERTY",
    )

    assert response.headers["location"] == "/en/test/kat-alogus/plugins/boefje/test-boefje/"
    assert "Invalid setting name" in list(request._messages)[0].message


def test_plugin_single_settings_add_view_no_schema(
    rf,
    my_user,
    organization,
    mock_mixins_katalogus,
    plugin_details,
    mock_organization_view_octopoes,
):
    mock_mixins_katalogus().get_plugin.return_value = plugin_details
    mock_mixins_katalogus().get_plugin_schema.return_value = None

    request = setup_request(rf.post("step_organization_setup", data={"boefje_id": 123}), my_user)
    response = PluginSingleSettingAddView.as_view()(
        request,
        organization_code=organization.code,
        plugin_type="boefje",
        plugin_id="test-plugin",
        setting_name="BAD_PROPERTY",
    )

    assert response.headers["location"] == "/en/test/kat-alogus/plugins/boefje/test-boefje/"

    messages = list(request._messages)
    assert "No plugin schema found. You do not need to add settings to enable this plugin." in messages[0].message
