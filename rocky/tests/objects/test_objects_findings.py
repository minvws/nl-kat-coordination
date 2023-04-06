from pytest_django.asserts import assertContains, assertNotContains
import pytest
from octopoes.models.tree import ReferenceTree
from rocky.views.ooi_findings import OOIFindingListView
from rocky.views.ooi_detail import OOIDetailView
from rocky.views.ooi_add import OOIAddView
from rocky.views.ooi_mute import MuteFindingView
from django.core.exceptions import PermissionDenied
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

MUTED_FINDING_TREE_DATA = {
    "root": {
        "reference": "Mute Network|testnetwork|KAT-000",
        "children": {"ooi": [{"reference": "Network|testnetwork", "children": {}}]},
    },
    "store": {
        "Network|testnetwork": {
            "object_type": "Network",
            "primary_key": "Network|testnetwork",
            "name": "testnetwork",
        },
        "Mute Network|testnetwork|KAT-000": {
            "object_type": "MuteFinding",
            "primary_key": "MuteFinding|Network|testnetwork|KAT-000",
            "ooi": "Network|testnetwork",
            "finding_type": "KATFindingType|KAT-000",
        },
    },
}


def test_ooi_finding_list(rf, client_member, mock_organization_view_octopoes):
    mock_organization_view_octopoes().get_tree.return_value = ReferenceTree.parse_obj(TREE_DATA)

    request = setup_request(rf.get("finding_list", {"ooi_id": "Network|testnetwork"}), client_member.user)
    response = OOIFindingListView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 200
    assert mock_organization_view_octopoes().get_tree.call_count == 1
    assertContains(response, "Add finding")


def test_mute_finding_button_is_visible(
    rf, admin_member, redteam_member, client_member, mock_organization_view_octopoes, mock_scheduler, mocker
):
    mocker.patch("katalogus.client.KATalogusClientV1")
    mock_organization_view_octopoes().get_tree.return_value = ReferenceTree.parse_obj(TREE_DATA)

    request_admin = setup_request(rf.get("ooi_detail", {"ooi_id": "Network|testnetwork"}), admin_member.user)
    response_admin = OOIDetailView.as_view()(request_admin, organization_code=admin_member.organization.code)

    request_redteam = setup_request(rf.get("ooi_detail", {"ooi_id": "Network|testnetwork"}), redteam_member.user)
    response_redteam = OOIDetailView.as_view()(request_redteam, organization_code=redteam_member.organization.code)

    request_client = setup_request(rf.get("ooi_detail", {"ooi_id": "Network|testnetwork"}), client_member.user)
    response_client = OOIDetailView.as_view()(request_client, organization_code=client_member.organization.code)

    assert response_admin.status_code == 200
    assert response_redteam.status_code == 200
    assert response_client.status_code == 200

    # No permissions to see mute findings button
    assertNotContains(response_admin, "Mute Finding")
    assertNotContains(response_client, "Mute Finding")

    # Redteam permission to see mute finding button
    assertContains(response_redteam, "Mute Finding")


def test_mute_finding_form_view(rf, admin_member, redteam_member, client_member, mock_organization_view_octopoes):

    request_admin = setup_request(
        rf.get("finding_mute", {"ooi_id": "Finding|Network|testnetwork|KAT-000"}), admin_member.user
    )
    with pytest.raises(PermissionDenied):
        MuteFindingView.as_view()(request_admin, organization_code=admin_member.organization.code)

    request_client = setup_request(
        rf.get("finding_mute", {"ooi_id": "Finding|Network|testnetwork|KAT-000"}), client_member.user
    )
    with pytest.raises(PermissionDenied):
        MuteFindingView.as_view()(request_client, organization_code=client_member.organization.code)

    request_redteam = setup_request(
        rf.get("finding_mute", {"ooi_id": "Finding|Network|testnetwork|KAT-000"}), redteam_member.user
    )
    response_redteam = MuteFindingView.as_view()(request_redteam, organization_code=redteam_member.organization.code)

    assert response_redteam.status_code == 200

    assertContains(response_redteam, "Reason:")
    assertContains(response_redteam, "Mute")
    assertContains(response_redteam, "Cancel")
    assertContains(response_redteam, "Mute finding: ")


def test_mute_finding_post(
    rf,
    redteam_member,
    mock_bytes_client,
    mock_scheduler,
    mock_organization_view_octopoes,
    lazy_task_list_with_boefje,
    mocker,
):

    # post from the finding mute view
    request = setup_request(
        rf.post(
            "finding_mute",
            {
                "ooi_type": "MuteFinding",
                "finding": "Finding|Network|testnetwork|KAT-000",
                "reason": "I want to mute this finding because I am testing.",
            },
        ),
        redteam_member.user,
    )
    # Uses same ooi_add post request to add a MuteFinding object
    response = OOIAddView.as_view()(request, organization_code=redteam_member.organization.code, ooi_type="MuteFinding")

    # Redirects to ooi_detail
    assert response.status_code == 302

    mocker.patch("katalogus.client.KATalogusClientV1")
    resulted_request = setup_request(rf.get(response.url), redteam_member.user)

    mock_organization_view_octopoes().get_tree.return_value = ReferenceTree.parse_obj(MUTED_FINDING_TREE_DATA)
    mock_scheduler.get_lazy_task_list.return_value = lazy_task_list_with_boefje

    resulted_response = OOIDetailView.as_view()(resulted_request, organization_code=redteam_member.organization.code)
    assert resulted_response.status_code == 200

    assertContains(resulted_response, "I want to mute this finding because I am testing.")
