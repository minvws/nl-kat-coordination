from django.urls import reverse, resolve
from pytest_django.asserts import assertContains

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


def test_ooi_tree(
    rf, my_user, organization, mock_scheduler, mock_organization_view_octopoes, lazy_task_list_with_boefje, mocker
):
    mocker.patch("katalogus.utils.get_katalogus")

    kwargs = {"organization_code": organization.code}
    url = reverse("ooi_tree", kwargs=kwargs)
    request = rf.get(url, {"ooi_id": "Network|testnetwork"})
    request.resolver_match = resolve(url)

    setup_request(request, my_user)

    mock_organization_view_octopoes().get_tree.return_value = ReferenceTree.parse_obj(TREE_DATA)

    response = OOIDetailView.as_view()(request, **kwargs)

    assert response.status_code == 200
    assert mock_organization_view_octopoes().get_tree.call_count == 2
    assertContains(response, "testnetwork")
    assertContains(response, "KAT-000")
