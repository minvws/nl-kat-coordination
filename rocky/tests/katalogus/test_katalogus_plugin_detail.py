import pytest
from django.core.exceptions import BadRequest
from django.http import Http404
from octopoes.models.pagination import Paginated
from octopoes.models.types import OOIType
from pytest_django.asserts import assertContains
from requests import HTTPError

from katalogus.views.plugin_detail import PluginDetailView
from tests.conftest import setup_request


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
    mock_mixins_katalogus().get_plugin.return_value = plugin_details
    mock_mixins_katalogus().get_plugin_schema.return_value = plugin_schema

    request = setup_request(rf.post("plugin_detail", data={"boefje_id": 123}), my_user)
    response = PluginDetailView.as_view()(
        request, organization_code=organization.code, plugin_type="boefje", plugin_id="test-plugin"
    )

    assertContains(response, "TestBoefje")
    assertContains(response, "Meows to the moon")
    assertContains(response, "testnetwork")


def test_plugin_detail_data_missing(
    rf,
    my_user,
    organization,
    mock_mixins_katalogus,
    plugin_details,
    plugin_schema,
    mock_organization_view_octopoes,
    network,
    lazy_task_list_with_boefje,
):
    request = setup_request(rf.post("plugin_detail"), my_user)
    with pytest.raises(BadRequest):
        PluginDetailView.as_view()(
            request, organization_code=organization.code, plugin_type="boefje", plugin_id="test-plugin"
        )


def test_plugin_detail_bad_plugin_id(
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
    mock_mixins_katalogus().get_plugin.side_effect = HTTPError(response=mocker.MagicMock(status_code=404))

    request = setup_request(rf.post("plugin_detail", data={"boefje_id": 123}), my_user)

    with pytest.raises(Http404):
        PluginDetailView.as_view()(
            request, organization_code=organization.code, plugin_type="boefje", plugin_id="bad-plugin"
        )
