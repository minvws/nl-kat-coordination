from urllib.parse import urlencode

from pytest_django.asserts import assertContains, assertNotContains

from octopoes.models.tree import ReferenceTree
from rocky.views.scan_profile import ScanProfileDetailView
from tests.conftest import setup_request
from tools.models import OrganizationMember, Indemnification

TREE_DATA = {
    "root": {
        "reference": "Network|testnetwork",
        "children": {"urls": [{"reference": "URL|testnetwork|https://scanme.org./", "children": {}}]},
    },
    "store": {
        "Network|testnetwork": {
            "object_type": "Network",
            "primary_key": "Network|testnetwork",
            "name": "testnetwork",
            "scan_profile": {
                "scan_profile_type": "declared",
                "reference": "Network|testnetwork",
                "level": 1,
            },
        },
        "HostnameHTTPURL|https|internet|scanme.org.|443|/": {
            "object_type": "HostnameHTTPURL",
            "scan_profile": {
                "scan_profile_type": "inherited",
                "reference": "HostnameHTTPURL|https|internet|scanme.org.|443|/",
                "level": 2,
            },
            "primary_key": "HostnameHTTPURL|https|internet|scanme.org.|443|/",
            "network": "Network|internet",
            "scheme": "https",
            "port": 443,
            "path": "/",
            "netloc": "Hostname|internet|scanme.org.",
        },
    },
}


def test_scan_profile(rf, my_user, organization, mock_scheduler, mock_organization_view_octopoes, mocker):
    mocker.patch("katalogus.utils.get_katalogus")
    mock_organization_view_octopoes().get_tree.return_value = ReferenceTree.parse_obj(TREE_DATA)

    request = setup_request(rf.get("scan_profile_detail", {"ooi_id": "Network|testnetwork"}), my_user)
    response = ScanProfileDetailView.as_view()(request, organization_code=organization.code)

    assert response.status_code == 200
    assert mock_organization_view_octopoes().get_tree.call_count == 2

    assertContains(response, "Set clearance level")


def test_scan_profile_submit(rf, my_user, organization, mock_scheduler, mock_organization_view_octopoes, mocker):
    mocker.patch("katalogus.utils.get_katalogus")
    mock_organization_view_octopoes().get_tree.return_value = ReferenceTree.parse_obj(TREE_DATA)

    # Passing query params in POST requests is not well-supported for RequestFactory it seems, hence the absolute path
    query_string = urlencode({"ooi_id": "Network|testnetwork"}, doseq=True)
    request = setup_request(
        rf.post(f"/en/{organization.code}/objects/scan-profile/?{query_string}", data={"level": "L1"}),
        my_user,
    )
    response = ScanProfileDetailView.as_view()(request, organization_code=organization.code)

    assert response.status_code == 302
    assert response.url == f"/en/{organization.code}/objects/scan-profile/?{query_string}"


def test_scan_profile_submit_no_indemnification(
    rf, my_user, organization, mock_scheduler, mock_organization_view_octopoes, mocker
):
    mocker.patch("katalogus.utils.get_katalogus")
    mock_organization_view_octopoes().get_tree.return_value = ReferenceTree.parse_obj(TREE_DATA)

    Indemnification.objects.get(user=my_user).delete()

    # Passing query params in POST requests is not well-supported for RequestFactory it seems, hence the absolute path
    query_string = urlencode({"ooi_id": "Network|testnetwork"}, doseq=True)
    request = setup_request(
        rf.post(f"/en/{organization.code}/objects/scan-profile/?{query_string}", data={"level": "L1"}),
        my_user,
    )
    response = ScanProfileDetailView.as_view()(request, organization_code=organization.code)

    assert response.status_code == 403


def test_scan_profile_no_permissions_acknowledged(
    rf, my_user, organization, mock_scheduler, mock_organization_view_octopoes, mocker
):
    mocker.patch("katalogus.utils.get_katalogus")
    mock_organization_view_octopoes().get_tree.return_value = ReferenceTree.parse_obj(TREE_DATA)

    member = OrganizationMember.objects.get(user=my_user)
    member.acknowledged_clearance_level = -1
    member.save()

    request = setup_request(rf.get("scan_profile_detail", {"ooi_id": "Network|testnetwork"}), my_user)
    response = ScanProfileDetailView.as_view()(request, organization_code=organization.code)

    assert response.status_code == 200
    assert mock_organization_view_octopoes().get_tree.call_count == 2

    assertNotContains(response, "Set clearance level")


def test_scan_profile_no_permissions_trusted(
    rf, my_user, organization, mock_scheduler, mock_organization_view_octopoes, mocker
):
    mock_organization_view_octopoes().get_tree.return_value = ReferenceTree.parse_obj(TREE_DATA)
    mocker.patch("katalogus.utils.get_katalogus")

    member = OrganizationMember.objects.get(user=my_user)
    member.trusted_clearance_level = -1
    member.save()

    request = setup_request(rf.get("scan_profile_detail", {"ooi_id": "Network|testnetwork"}), my_user)
    response = ScanProfileDetailView.as_view()(request, organization_code=organization.code)

    assert response.status_code == 200
    assert mock_organization_view_octopoes().get_tree.call_count == 2

    assertNotContains(response, "Set clearance level")
