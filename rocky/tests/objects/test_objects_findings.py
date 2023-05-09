import pytest
from django.core.exceptions import PermissionDenied
from pytest_django.asserts import assertContains, assertNotContains

from octopoes.models.tree import ReferenceTree
from rocky.views.ooi_add import OOIAddView
from rocky.views.ooi_detail import OOIDetailView
from rocky.views.ooi_findings import OOIFindingListView
from rocky.views.ooi_mute import MuteFindingView
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
        "reference": "MutedFinding|Network|testnetwork|KAT-000",
        "children": {"ooi": [{"reference": "Finding|Network|testnetwork|KAT-000", "children": {}}]},
    },
    "store": {
        "MutedFinding|Network|testnetwork|KAT-000": {
            "object_type": "MutedFinding",
            "primary_key": "MutedFinding|Network|testnetwork|KAT-000",
            "finding": "Finding|Network|testnetwork|KAT-000",
            "reason": "Hallo",
        },
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


def test_ooi_finding_list(rf, client_member, mock_organization_view_octopoes):
    mock_organization_view_octopoes().get_tree.return_value = ReferenceTree.parse_obj(TREE_DATA)

    request = setup_request(rf.get("finding_list", {"ooi_id": "Network|testnetwork"}), client_member.user)
    response = OOIFindingListView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 200
    assert mock_organization_view_octopoes().get_tree.call_count == 1
    assertContains(response, "Add finding")


@pytest.mark.parametrize("member", ["superuser_member", "redteam_member"])
def test_mute_finding_button_is_visible(request, member, rf, mock_organization_view_octopoes, mock_scheduler, mocker):
    mocker.patch("katalogus.client.KATalogusClientV1")
    mock_organization_view_octopoes().get_tree.return_value = ReferenceTree.parse_obj(TREE_DATA)

    member = request.getfixturevalue(member)

    response = OOIDetailView.as_view()(
        setup_request(rf.get("ooi_detail", {"ooi_id": "Network|testnetwork"}), member.user),
        organization_code=member.organization.code,
    )

    assert response.status_code == 200
    assertContains(response, "Mute Finding")


@pytest.mark.parametrize("member", ["superuser_member", "redteam_member"])
def test_mute_finding_form_view(request, member, rf, mock_organization_view_octopoes):
    member = request.getfixturevalue(member)
    response = MuteFindingView.as_view()(
        setup_request(rf.get("finding_mute", {"ooi_id": "Finding|Network|testnetwork|KAT-000"}), member.user),
        organization_code=member.organization.code,
    )

    assert response.status_code == 200

    assertContains(response, "Reason:")
    assertContains(response, "Mute")
    assertContains(response, "Cancel")
    assertContains(response, "Mute finding: ")


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
    muted_finding = MUTED_FINDING_TREE_DATA["store"]["MutedFinding|Network|testnetwork|KAT-000"]
    request = setup_request(
        rf.post(
            "finding_mute",
            {
                "ooi_type": muted_finding["object_type"],
                "finding": muted_finding["finding"],
                "reason": muted_finding["reason"],
            },
        ),
        redteam_member.user,
    )
    # Uses same ooi_add post request to add a MuteFinding object
    response = OOIAddView.as_view()(
        request, organization_code=redteam_member.organization.code, ooi_type="MutedFinding"
    )

    # Redirects to ooi_detail
    assert response.status_code == 302

    mocker.patch("katalogus.client.KATalogusClientV1")
    resulted_request = setup_request(rf.get(response.url), redteam_member.user)

    mock_organization_view_octopoes().get_tree.return_value = ReferenceTree.parse_obj(MUTED_FINDING_TREE_DATA)
    mock_scheduler.get_lazy_task_list.return_value = lazy_task_list_with_boefje

    resulted_response = OOIDetailView.as_view()(resulted_request, organization_code=redteam_member.organization.code)

    assert resulted_response.status_code == 200
    assertContains(resulted_response, "Reason")
    assertContains(resulted_response, "Muted Network|testnetwork|KAT-000")
    assertContains(resulted_response, "MutedFinding")
    assertContains(resulted_response, muted_finding["reason"])
    assertContains(resulted_response, "KAT-000 @ testnetwork")
