from django.urls import reverse, resolve
from pytest_django.asserts import assertContains

from octopoes.models.tree import ReferenceTree
from rocky.views.ooi_tree import OOITreeView
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


def test_ooi_tree(rf, my_user, organization, mock_organization_view_octopoes):
    mock_organization_view_octopoes().get_tree.return_value = ReferenceTree.parse_obj(TREE_DATA)

    request = setup_request(rf.get("ooi_tree", {"ooi_id": "Network|testnetwork", "view": "table"}), my_user)
    request.resolver_match = resolve(reverse("ooi_tree", kwargs={"organization_code": organization.code}))
    response = OOITreeView.as_view()(request, organization_code=organization.code)

    assert response.status_code == 200
    assert mock_organization_view_octopoes().get_tree.call_count == 1
    assertContains(response, "testnetwork")
    assertContains(response, "KAT-000")

    assertContains(response, "?view=table")
    assertContains(response, "?view=condensed")
