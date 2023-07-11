import pytest
from account.views import AccountView
from katalogus.views.plugin_detail import PluginDetailView
from pytest_django.asserts import assertContains, assertNotContains

from octopoes.models.pagination import Paginated
from octopoes.models.types import OOIType
from tests.conftest import setup_request


def test_is_not_red_team(superuser_member):
    assert not superuser_member.is_redteam


def test_is_red_team(redteam_member):
    assert redteam_member.is_redteam


def test_is_not_admin(superuser_member):
    assert not superuser_member.is_admin


def test_is_admin(admin_member):
    assert admin_member.is_admin


def test_indemnification_present(superuser_member):
    assert superuser_member.user.indemnification_set.exists()


def test_account_detail_perms(rf, superuser_member, admin_member, redteam_member, client_member):
    response_superuser = AccountView.as_view()(
        setup_request(rf.get("account_detail"), superuser_member.user),
        organization_code=superuser_member.organization.code,
    )

    response_admin = AccountView.as_view()(
        setup_request(rf.get("account_detail"), admin_member.user), organization_code=admin_member.organization.code
    )

    response_redteam = AccountView.as_view()(
        setup_request(rf.get("account_detail"), redteam_member.user), organization_code=redteam_member.organization.code
    )

    response_client = AccountView.as_view()(
        setup_request(rf.get("account_detail"), client_member.user), organization_code=client_member.organization.code
    )
    assert response_superuser.status_code == 200
    assert response_admin.status_code == 200
    assert response_redteam.status_code == 200
    assert response_client.status_code == 200

    # There is already text having OOI clearance outside the perms sections, so header tags must be included
    check_text = "<h2>OOI clearance</h2>"

    assertContains(response_superuser, check_text)
    assertContains(response_redteam, check_text)

    assertNotContains(response_admin, check_text)
    assertNotContains(response_client, check_text)


@pytest.mark.parametrize("member", ["superuser_member", "redteam_member"])
def test_plugin_settings_list_perms(
    request,
    member,
    rf,
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

    member = request.getfixturevalue(member)

    response = PluginDetailView.as_view()(
        setup_request(rf.get("plugin_detail"), member.user),
        organization_code=member.organization.code,
        plugin_type="boefje",
        plugin_id="test-plugin",
    )

    assert response.status_code == 200
    assertContains(response, "Overview of settings:")
    assertContains(response, "Object list")


@pytest.mark.parametrize("member", ["admin_member", "client_member"])
def test_plugin_settings_list_perms_2(
    request,
    member,
    rf,
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

    member = request.getfixturevalue(member)

    response = PluginDetailView.as_view()(
        setup_request(rf.get("plugin_detail"), member.user),
        organization_code=member.organization.code,
        plugin_type="boefje",
        plugin_id="test-plugin",
    )

    assert response.status_code == 200

    assertNotContains(response, "Overview of settings:")
