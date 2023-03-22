from pytest_django.asserts import assertContains

from katalogus.views.plugin_settings_edit import PluginSettingsUpdateView
from tests.conftest import setup_request


def test_plugin_settings_edit_view(
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
    response = PluginSettingsUpdateView.as_view()(
        request,
        organization_code=organization.code,
        plugin_type="boefje",
        plugin_id="test-plugin",
        setting_name="TEST_PROPERTY",
    )

    assertContains(response, "TestBoefje")
    assertContains(response, "Edit setting")
    assertContains(response, "TEST_PROPERTY")
    assertContains(response, "Update setting")
