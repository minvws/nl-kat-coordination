from urllib.parse import urlencode

import pytest
from django.http import HttpResponseRedirect
from katalogus.client import Plugin
from pytest_django.asserts import assertContains, assertNotContains
from tools.enums import SCAN_LEVEL
from tools.models import Indemnification

from octopoes.models.tree import ReferenceTree
from rocky.views.ooi_detail import OOIDetailView
from tests.conftest import setup_request

TREE_DATA = {
    "root": {
        "reference": "Finding|Network|testnetwork|KAT-000",
        "children": {"ooi": [{"reference": "Network|testnetwork", "children": {}}]},
    },
    "store": {
        "Network|testnetwork": {
            "object_type": "Network",
            "primary_key": "Network|testnetwork",
            "name": "testnetwork",
        },
        "Finding|Network|testnetwork|KAT-000": {
            "object_type": "Finding",
            "primary_key": "Finding|Network|testnetwork|KAT-000",
            "ooi": "Network|testnetwork",
            "finding_type": "KATFindingType|KAT-000",
        },
    },
}


def test_ooi_detail(
    rf,
    client_member,
    mock_scheduler,
    mock_organization_view_octopoes,
    lazy_task_list_with_boefje,
    mocker,
):
    mocker.patch("katalogus.client.KATalogusClientV1")

    request = setup_request(rf.get("ooi_detail", {"ooi_id": "Network|testnetwork"}), client_member.user)

    mock_organization_view_octopoes().get_tree.return_value = ReferenceTree.parse_obj(TREE_DATA)
    mock_scheduler.get_lazy_task_list.return_value = lazy_task_list_with_boefje

    response = OOIDetailView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 200
    assert mock_organization_view_octopoes().get_tree.call_count == 2
    assertContains(response, "Object")
    assertContains(response, "Hostname|internet|mispo.es")

    assertContains(response, "Plugin")
    assertContains(response, "test-boefje")
    assertContains(
        response, f'href="/en/{client_member.organization.code}/kat-alogus/plugins/boefje/test-boefje/">test-boefje</a>'
    )
    assertContains(response, "Status")
    assertContains(response, "Completed")
    assertContains(response, "Created date")
    assertContains(response, "9, 2022, 11:53 a.m.")


def test_ooi_detail_start_scan(
    rf,
    client_member,
    mock_organization_view_octopoes,
    mocker,
    network,
):
    mock_katalogus = mocker.patch("katalogus.client.KATalogusClientV1")
    mocker.patch("katalogus.views.mixins.client")

    mock_organization_view_octopoes().get_tree.return_value = ReferenceTree.parse_obj(TREE_DATA)
    mock_organization_view_octopoes().get.return_value = network
    mock_katalogus().get_plugin.return_value = Plugin(
        id="nmap",
        repository_id="",
        name="",
        description="",
        environment_keys=[],
        type="boefje",
        scan_level=SCAN_LEVEL.L2,
        consumes=[],
        produces=[],
    )

    # Passing query params in POST requests is not well-supported for RequestFactory it seems, hence the absolute path
    query_string = urlencode({"ooi_id": network.reference}, doseq=True)

    request = setup_request(
        rf.post(
            f"/en/{client_member.organization.code}/objects/details/?{query_string}",
            data={
                "boefje_id": "nmap",
                "action": "start_scan",
            },
        ),
        client_member.user,
    )
    response = OOIDetailView.as_view()(request, organization_code=client_member.organization.code)

    assert mock_organization_view_octopoes().get_tree.call_count == 1
    assert isinstance(response, HttpResponseRedirect)
    assert response.status_code == 302
    assert response.url == f"/en/{client_member.organization.code}/tasks/"


def test_ooi_detail_start_scan_no_indemnification(
    rf,
    client_member,
    mock_scheduler,
    mock_organization_view_octopoes,
    lazy_task_list_with_boefje,
    mocker,
    network,
):
    mocker.patch("katalogus.client.KATalogusClientV1")

    mock_organization_view_octopoes().get_tree.return_value = ReferenceTree.parse_obj(TREE_DATA)
    mock_organization_view_octopoes().get.return_value = network

    Indemnification.objects.get(user=client_member.user).delete()

    # Passing query params in POST requests is not well-supported for RequestFactory it seems, hence the absolute path
    query_string = urlencode({"ooi_id": network.reference}, doseq=True)
    request = setup_request(
        rf.post(
            f"/en/{client_member.organization.code}/objects/details/?{query_string}",
            data={
                "boefje_id": "nmap",
                "action": "start_scan",
            },
        ),
        client_member.user,
    )
    response = OOIDetailView.as_view()(request, organization_code=client_member.organization.code)

    assert mock_organization_view_octopoes().get_tree.call_count == 2
    assertContains(response, "Object details", status_code=403)
    assertContains(response, "Indemnification not present", status_code=403)


def test_ooi_detail_start_scan_no_action(
    rf,
    client_member,
    mock_scheduler,
    mock_organization_view_octopoes,
    lazy_task_list_with_boefje,
    mocker,
    network,
):
    mocker.patch("katalogus.client.KATalogusClientV1")

    mock_organization_view_octopoes().get_tree.return_value = ReferenceTree.parse_obj(TREE_DATA)
    mock_organization_view_octopoes().get.return_value = network

    # Passing query params in POST requests is not well-supported for RequestFactory it seems, hence the absolute path
    query_string = urlencode({"ooi_id": network.reference}, doseq=True)
    request = setup_request(
        rf.post(
            f"/en/{client_member.organization.code}/objects/details/?{query_string}",
            data={
                "boefje_id": "nmap",
            },
        ),
        client_member.user,
    )
    response = OOIDetailView.as_view()(request, organization_code=client_member.organization.code)

    assert mock_organization_view_octopoes().get_tree.call_count == 2
    assertContains(response, "Object details", status_code=404)


@pytest.mark.parametrize("member", ["superuser_member", "admin_member", "redteam_member"])
def test_delete_perms_ooi_detail(
    request,
    member,
    rf,
    mock_scheduler,
    mock_organization_view_octopoes,
    lazy_task_list_with_boefje,
    mocker,
):
    member = request.getfixturevalue(member)
    mocker.patch("katalogus.client.KATalogusClientV1")
    mock_organization_view_octopoes().get_tree.return_value = ReferenceTree.parse_obj(TREE_DATA)
    mock_scheduler.get_lazy_task_list.return_value = lazy_task_list_with_boefje

    response = OOIDetailView.as_view()(
        setup_request(rf.get("ooi_detail", {"ooi_id": "Network|testnetwork"}), member.user),
        organization_code=member.organization.code,
    )

    assert response.status_code == 200
    assertContains(response, "Delete")


def test_delete_perms_ooi_detail_clients(
    rf,
    client_member,
    mock_scheduler,
    mock_organization_view_octopoes,
    lazy_task_list_with_boefje,
    mocker,
):
    mocker.patch("katalogus.client.KATalogusClientV1")
    mock_organization_view_octopoes().get_tree.return_value = ReferenceTree.parse_obj(TREE_DATA)
    mock_scheduler.get_lazy_task_list.return_value = lazy_task_list_with_boefje

    response = OOIDetailView.as_view()(
        setup_request(rf.get("ooi_detail", {"ooi_id": "Network|testnetwork"}), client_member.user),
        organization_code=client_member.organization.code,
    )
    assert response.status_code == 200
    assertNotContains(response, "Delete")


def test_ooi_detail_start_scan_perms(
    rf,
    client_member,
    mock_scheduler,
    mock_organization_view_octopoes,
    lazy_task_list_with_boefje,
    mocker,
):
    mocker.patch("katalogus.client.KATalogusClientV1")
    request = setup_request(rf.get("ooi_detail", {"ooi_id": "Network|testnetwork"}), client_member.user)

    mock_organization_view_octopoes().get_tree.return_value = ReferenceTree.parse_obj(TREE_DATA)
    mock_scheduler.get_lazy_task_list.return_value = lazy_task_list_with_boefje

    response = OOIDetailView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 200
    assertNotContains(response, "Start Scan")
