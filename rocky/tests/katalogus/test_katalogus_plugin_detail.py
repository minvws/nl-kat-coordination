from katalogus.views.plugin_detail import PluginDetailView
from pytest_django.asserts import assertContains

from tests.conftest import setup_request


def test_plugin_detail_view(
    rf,
    superuser_member,
    mock_mixins_katalogus,
    plugin_details,
    mock_organization_view_octopoes,
    mock_scheduler_client_task_list,
):
    mock_mixins_katalogus().get_plugin.return_value = plugin_details

    request = setup_request(rf.get("plugin_detail"), superuser_member.user)
    response = PluginDetailView.as_view()(
        request,
        organization_code=superuser_member.organization.code,
        plugin_id="test-plugin",
    )

    assertContains(response, "TestBoefje")
    assertContains(response, "Completed")
    assertContains(response, "Consumes")
    assertContains(response, plugin_details.description)


def test_plugin_detail_view_no_consumes(
    rf,
    superuser_member,
    mock_mixins_katalogus,
    plugin_details,
    mock_organization_view_octopoes,
    mock_scheduler_client_task_list,
):
    plugin_details.consumes = []
    mock_mixins_katalogus().get_plugin.return_value = plugin_details

    request = setup_request(rf.get("plugin_detail"), superuser_member.user)
    response = PluginDetailView.as_view()(
        request,
        organization_code=superuser_member.organization.code,
        plugin_id="test-plugin",
    )

    assertContains(response, "TestBoefje does not need any input objects.")
