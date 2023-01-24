import pytest
from pytest_django.asserts import assertContains

from katalogus.views.plugin_detail import PluginDetailView
from octopoes.models.pagination import Paginated
from octopoes.models.types import OOIType
from tests.conftest import setup_request


@pytest.fixture()
def mock_mixins_katalogus(mocker):
    return mocker.patch("katalogus.views.mixins.get_katalogus")


def test_plugin_detail(
    rf,
    my_user,
    organization,
    mock_mixins_katalogus,
    plugin_details,
    plugin_schema,
    mock_organization_view_octopoes,
    network,
    mocker,
    lazy_task_list_with_boefje,
):
    mock_scheduler_client = mocker.patch("katalogus.views.plugin_detail.scheduler")
    mock_scheduler_client.client.get_lazy_task_list.return_value = lazy_task_list_with_boefje

    mock_organization_view_octopoes().list.return_value = Paginated[OOIType](count=1, items=[network])
    mock_mixins_katalogus().get_plugin_details.return_value = plugin_details
    mock_mixins_katalogus().get_plugin_schema.return_value = plugin_schema

    request = setup_request(rf.post("step_organization_setup"), my_user)
    response = PluginDetailView.as_view()(
        request, organization_code=organization.code, plugin_type="boefje", plugin_id="test-plugin"
    )

    assertContains(response, "TestBoefje")
    assertContains(response, "Meows to the moon")
    assertContains(response, "testnetwork")
