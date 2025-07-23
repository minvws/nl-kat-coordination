from urllib.parse import urlencode

import pytest
from pytest_django.asserts import assertContains, assertNotContains

from katalogus.models import Boefje
from octopoes.models.tree import ReferenceTree
from openkat.models import Indemnification
from openkat.views.ooi_detail import OOIDetailView
from tests.conftest import setup_request

TREE_DATA = {
    "root": {
        "reference": "Finding|Network|testnetwork|KAT-000",
        "children": {"ooi": [{"reference": "Network|testnetwork", "children": {}}]},
    },
    "store": {
        "Network|testnetwork": {"object_type": "Network", "primary_key": "Network|testnetwork", "name": "testnetwork"},
        "Finding|Network|testnetwork|KAT-000": {
            "object_type": "Finding",
            "primary_key": "Finding|Network|testnetwork|KAT-000",
            "ooi": "Network|testnetwork",
            "finding_type": "KATFindingType|KAT-000",
        },
    },
}


def test_ooi_detail(rf, client_member, octopoes_api_connector, task_db, tree):
    request = setup_request(rf.get("ooi_detail", {"ooi_id": "Network|testnetwork"}), client_member.user)

    response = OOIDetailView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 200
    assert octopoes_api_connector.get_tree.call_count == 1
    assertContains(response, "Object")
    assertContains(response, "Network|testnetwork")

    assertContains(response, "Plugin")
    assertContains(response, "TestBoefje")
    assertContains(
        response, f'href="/en/{client_member.organization.code}/kat-alogus/plugins/boefje/test-boefje/">TestBoefje</a>'
    )
    assertContains(response, "Status")
    assertContains(response, "Completed")
    assertContains(response, "Created date")


def test_ooi_detail_start_scan(rf, client_member, octopoes_api_connector, plugins, mock_scheduler, tree, network):
    octopoes_api_connector.get.return_value = network

    # Passing query params in POST requests is not well-supported for RequestFactory it seems, hence the absolute path
    query_string = urlencode({"ooi_id": network.reference}, doseq=True)

    request = setup_request(
        rf.post(
            f"/en/{client_member.organization.code}/objects/details/?{query_string}",
            data={"boefje_id": Boefje.objects.get(plugin_id="nmap").id, "action": "start_scan"},
        ),
        client_member.user,
    )
    response = OOIDetailView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 200


def test_ooi_detail_start_scan_no_indemnification(rf, client_member, octopoes_api_connector, network, plugins):
    octopoes_api_connector.get_tree.return_value = ReferenceTree.model_validate(TREE_DATA)
    octopoes_api_connector.get.return_value = network
    Indemnification.objects.get(user=client_member.user).delete()

    # Passing query params in POST requests is not well-supported for RequestFactory it seems, hence the absolute path
    query_string = urlencode({"ooi_id": network.reference}, doseq=True)
    request = setup_request(
        rf.post(
            f"/en/{client_member.organization.code}/objects/details/?{query_string}",
            data={"boefje_id": Boefje.objects.get(plugin_id="nmap").id, "action": "start_scan"},
        ),
        client_member.user,
    )
    response = OOIDetailView.as_view()(request, organization_code=client_member.organization.code)

    assert octopoes_api_connector.get_tree.call_count == 1
    assertContains(response, "Object details")
    assertContains(response, "Indemnification not present")


def test_ooi_detail_start_scan_no_action(rf, client_member, mock_scheduler, octopoes_api_connector, network):
    octopoes_api_connector.get_tree.return_value = ReferenceTree.model_validate(TREE_DATA)
    octopoes_api_connector.get.return_value = network

    # Passing query params in POST requests is not well-supported for RequestFactory it seems, hence the absolute path
    query_string = urlencode({"ooi_id": network.reference}, doseq=True)
    request = setup_request(
        rf.post(f"/en/{client_member.organization.code}/objects/details/?{query_string}", data={"boefje_id": "nmap"}),
        client_member.user,
    )
    response = OOIDetailView.as_view()(request, organization_code=client_member.organization.code)

    assert octopoes_api_connector.get_tree.call_count == 1
    assertContains(response, "Object details")


@pytest.mark.parametrize("member", ["superuser_member", "admin_member", "redteam_member"])
def test_delete_perms_ooi_detail(request, member, rf, mock_scheduler, octopoes_api_connector):
    member = request.getfixturevalue(member)
    octopoes_api_connector.get_tree.return_value = ReferenceTree.model_validate(TREE_DATA)

    response = OOIDetailView.as_view()(
        setup_request(rf.get("ooi_detail", {"ooi_id": "Network|testnetwork"}), member.user),
        organization_code=member.organization.code,
    )

    assert response.status_code == 200
    assertContains(response, "Delete")


def test_delete_perms_ooi_detail_clients(rf, client_member, mock_scheduler, octopoes_api_connector):
    octopoes_api_connector.get_tree.return_value = ReferenceTree.model_validate(TREE_DATA)

    response = OOIDetailView.as_view()(
        setup_request(rf.get("ooi_detail", {"ooi_id": "Network|testnetwork"}), client_member.user),
        organization_code=client_member.organization.code,
    )
    assert response.status_code == 200
    assertNotContains(response, "Delete")


def test_ooi_detail_start_scan_perms(rf, client_member, mock_scheduler, octopoes_api_connector):
    request = setup_request(rf.get("ooi_detail", {"ooi_id": "Network|testnetwork"}), client_member.user)

    octopoes_api_connector.get_tree.return_value = ReferenceTree.model_validate(TREE_DATA)

    response = OOIDetailView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 200
    assertNotContains(response, "Start Scan")
