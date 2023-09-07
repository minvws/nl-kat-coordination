from katalogus.views.boefje_detail import PluginDetailView
from pytest_django.asserts import assertContains

from tests.conftest import setup_request


def test_boefje_detail_view(
    rf,
    superuser_member,
    mock_mixins_katalogus,
    boefje_details,
    mock_organization_view_octopoes,
    mock_scheduler_client_task_list,
):
    mock_mixins_katalogus().get_plugin.return_value = boefje_details

    request = setup_request(rf.get("boefje_detail"), superuser_member.user)
    response = PluginDetailView.as_view()(
        request,
        organization_code=superuser_member.organization.code,
        plugin_id="test-plugin",
    )

    assertContains(response, "TestBoefje")
    assertContains(response, "Completed")
    assertContains(response, "Consumes")
    assertContains(response, "TestBoefje is able to scan the following object types")


def test_boefje_detail_view_no_consumes(
    rf,
    superuser_member,
    mock_mixins_katalogus,
    boefje_details,
    mock_organization_view_octopoes,
    mock_scheduler_client_task_list,
):
    boefje_details.consumes = []
    mock_mixins_katalogus().get_plugin.return_value = boefje_details

    request = setup_request(rf.get("boefje_detail"), superuser_member.user)
    response = PluginDetailView.as_view()(
        request,
        organization_code=superuser_member.organization.code,
        plugin_id="test-plugin",
    )

    assertContains(response, "TestBoefje does not need any input objects.")
