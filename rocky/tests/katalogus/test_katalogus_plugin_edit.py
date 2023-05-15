from katalogus.views.plugin_settings_edit import PluginSettingsUpdateView
from pytest_django.asserts import assertContains

from tests.conftest import setup_request


def test_plugin_settings_edit_view(
    rf,
    superuser_member,
    mock_mixins_katalogus,
    plugin_details,
    plugin_schema,
    mock_organization_view_octopoes,
):
    mock_mixins_katalogus().get_plugin.return_value = plugin_details
    mock_mixins_katalogus().get_plugin_schema.return_value = plugin_schema

    request = setup_request(rf.post("plugin_settings_edit", data={"boefje_id": 123}), superuser_member.user)
    response = PluginSettingsUpdateView.as_view()(
        request,
        organization_code=superuser_member.organization.code,
        plugin_type="boefje",
        plugin_id="test-plugin",
        setting_name="TEST_PROPERTY",
    )

    assertContains(response, "TestBoefje")
    assertContains(response, "Edit setting")
    assertContains(response, "TEST_PROPERTY")
    assertContains(response, "Update setting")
