import csv
import io
import json
from django.urls import reverse, resolve
from octopoes.models.exception import ObjectNotFoundException
from pytest_django.asserts import assertContains
from octopoes.models import ScanLevel, ScanProfileType
from octopoes.models.ooi.network import Network
from octopoes.models.pagination import Paginated
from octopoes.models.types import OOIType
from rocky.views.ooi_list import OOIListView, OOIListExportView
from tests.conftest import setup_request
from tools.models import Indemnification


def test_ooi_list(rf, superuser_member, organization, mock_organization_view_octopoes):
    kwargs = {"organization_code": organization.code}
    url = reverse("ooi_list", kwargs=kwargs)
    request = rf.get(url)
    request.resolver_match = resolve(url)

    setup_request(request, superuser_member.user)

    mock_organization_view_octopoes().list.return_value = Paginated[OOIType](
        count=200, items=[Network(name="testnetwork")] * 150
    )

    response = OOIListView.as_view()(request, organization_code=organization.code)

    assert response.status_code == 200
    assert mock_organization_view_octopoes().list.call_count == 2
    assertContains(response, "testnetwork")


def test_ooi_list_with_clearance_type_filter_and_clearance_level_filter(
    rf, superuser_member, organization, mock_organization_view_octopoes
):
    kwargs = {"organization_code": organization.code}
    url = reverse("ooi_list", kwargs=kwargs)
    request = rf.get(
        url,
        {"clearance_level": [0, 1], "clearance_type": ["declared", "inherited"]},
    )
    request.resolver_match = resolve(url)

    setup_request(request, superuser_member.user)

    mock_organization_view_octopoes().list.return_value = Paginated[OOIType](
        count=200, items=[Network(name="testnetwork")] * 150
    )

    response = OOIListView.as_view()(request, organization_code=organization.code)

    assert response.status_code == 200
    assert mock_organization_view_octopoes().list.call_count == 2

    list_call_0 = mock_organization_view_octopoes().list.call_args_list[0]
    assert list_call_0.kwargs["limit"] == 0
    assert list_call_0.kwargs["scan_level"] == {ScanLevel.L0, ScanLevel.L1}
    assert list_call_0.kwargs["scan_profile_type"] == {ScanProfileType.DECLARED, ScanProfileType.INHERITED}

    list_call_1 = mock_organization_view_octopoes().list.call_args_list[1]
    assert list_call_1.kwargs["limit"] == 150
    assert list_call_1.kwargs["offset"] == 0
    assert list_call_1.kwargs["scan_level"] == {ScanLevel.L0, ScanLevel.L1}
    assert list_call_1.kwargs["scan_profile_type"] == {ScanProfileType.DECLARED, ScanProfileType.INHERITED}

    assertContains(response, "testnetwork")
    assertContains(response, "Showing 150 of 200 objects")


def test_ooi_list_delete_multiple(rf, superuser_member, organization, mock_organization_view_octopoes):
    kwargs = {"organization_code": organization.code}
    url = reverse("ooi_list", kwargs=kwargs)
    superuser_member.trusted_clearance_level = 0
    superuser_member.acknowledged_clearance_level = 0
    superuser_member.save()

    request = rf.post(
        url,
        data={
            "ooi": ["Network|internet", "Hostname|internet|scanme.org."],
            "scan-profile": "L0",
            "action": "delete",
        },
    )
    setup_request(request, superuser_member.user)
    response = OOIListView.as_view()(request, organization_code=organization.code)

    assert response.status_code == 200
    assert mock_organization_view_octopoes().list.call_count == 2
    assert mock_organization_view_octopoes().delete.call_count == 2


def test_ooi_list_delete_none(rf, superuser_member, organization, mock_organization_view_octopoes):
    kwargs = {"organization_code": organization.code}
    url = reverse("ooi_list", kwargs=kwargs)

    request = rf.post(url, data={"ooi": [], "scan-profile": "L0", "action": "delete"})
    setup_request(request, superuser_member.user)

    superuser_member.acknowledged_clearance_level = 0
    superuser_member.save()
    response = OOIListView.as_view()(request, organization_code=organization.code)

    assert response.status_code == 422


def test_ooi_list_unknown_action(rf, superuser_member, organization, mock_organization_view_octopoes):
    kwargs = {"organization_code": organization.code}
    url = reverse("ooi_list", kwargs=kwargs)

    request = rf.post(url, data={"ooi": ["Network|internet"], "scan-profile": "L0", "action": "None"})
    setup_request(request, superuser_member.user)

    superuser_member.acknowledged_clearance_level = 0
    superuser_member.save()
    response = OOIListView.as_view()(request, organization_code=organization.code)

    assert response.status_code == 404


def test_update_scan_profile_multiple(rf, superuser_member, organization, mock_organization_view_octopoes):
    kwargs = {"organization_code": organization.code}
    url = reverse("ooi_list", kwargs=kwargs)
    superuser_member.trusted_clearance_level = 1
    superuser_member.acknowledged_clearance_level = 1
    superuser_member.save()
    request = rf.post(
        url,
        data={
            "ooi": ["Network|internet", "Hostname|internet|scanme.org."],
            "scan-profile": "L1",
            "action": "update-scan-profile",
        },
    )
    setup_request(request, superuser_member.user)
    response = OOIListView.as_view()(request, organization_code=organization.code)

    assert response.status_code == 200
    assert mock_organization_view_octopoes().save_scan_profile.call_count == 2


def test_update_scan_profile_single(rf, superuser_member, organization, mock_organization_view_octopoes):
    kwargs = {"organization_code": organization.code}
    url = reverse("ooi_list", kwargs=kwargs)
    superuser_member.trusted_clearance_level = 4
    superuser_member.acknowledged_clearance_level = 4
    superuser_member.save()

    request = rf.post(
        url,
        data={
            "ooi": ["Hostname|internet|scanme.org."],
            "scan-profile": "L4",
            "action": "update-scan-profile",
        },
    )

    setup_request(request, superuser_member.user)
    response = OOIListView.as_view()(request, organization_code=organization.code)

    assert response.status_code == 200
    assert mock_organization_view_octopoes().save_scan_profile.call_count == 1


def test_update_scan_profile_to_inherit(rf, superuser_member, organization, mock_organization_view_octopoes):
    kwargs = {"organization_code": organization.code}
    url = reverse("ooi_list", kwargs=kwargs)

    request = rf.post(
        url,
        data={
            "ooi": ["Hostname|internet|scanme.org."],
            "scan-profile": "inherit",
            "action": "update-scan-profile",
        },
    )
    setup_request(request, superuser_member.user)
    response = OOIListView.as_view()(request, organization_code=organization.code)

    assert response.status_code == 200
    assert mock_organization_view_octopoes().save_scan_profile.call_count == 1


def test_update_scan_profile_to_inherit_connection_error(
    rf, superuser_member, organization, mock_organization_view_octopoes
):
    mock_organization_view_octopoes().save_scan_profile.side_effect = ConnectionError
    kwargs = {"organization_code": organization.code}
    url = reverse("ooi_list", kwargs=kwargs)

    request = rf.post(
        url,
        data={
            "ooi": ["Hostname|internet|scanme.org."],
            "scan-profile": "inherit",
            "action": "update-scan-profile",
        },
    )
    setup_request(request, superuser_member.user)
    response = OOIListView.as_view()(request, organization_code=organization.code)

    assert response.status_code == 500


def test_update_scan_profile_to_inherit_object_not_found(
    rf, superuser_member, organization, mock_organization_view_octopoes
):
    mock_organization_view_octopoes().save_scan_profile.side_effect = ObjectNotFoundException("nothing found")
    kwargs = {"organization_code": organization.code}
    url = reverse("ooi_list", kwargs=kwargs)

    request = rf.post(
        url,
        data={
            "ooi": ["Hostname|internet|scanme.org."],
            "scan-profile": "inherit",
            "action": "update-scan-profile",
        },
    )
    setup_request(request, superuser_member.user)
    response = OOIListView.as_view()(request, organization_code=organization.code)

    assert response.status_code == 404


def test_update_scan_profiles_forbidden_acknowledged(
    rf, superuser_member, organization, mock_organization_view_octopoes
):
    kwargs = {"organization_code": organization.code}
    url = reverse("ooi_list", kwargs=kwargs)

    request = rf.post(
        url,
        data={
            "ooi": ["Network|internet", "Hostname|internet|scanme.org."],
            "scan-profile": "L1",
            "action": "update-scan-profile",
        },
    )

    superuser_member.acknowledged_clearance_level = -1
    superuser_member.save()

    setup_request(request, superuser_member.user)

    response = OOIListView.as_view()(request, organization_code=organization.code)

    assert response.status_code == 403


def test_update_scan_profiles_forbidden_trusted(rf, superuser_member, organization, mock_organization_view_octopoes):
    kwargs = {"organization_code": organization.code}
    url = reverse("ooi_list", kwargs=kwargs)

    request = rf.post(
        url,
        data={
            "ooi": ["Network|internet"],
            "scan-profile": "L1",
            "action": "update-scan-profile",
        },
    )

    superuser_member.trusted_clearance_level = -1
    superuser_member.save()

    setup_request(request, superuser_member.user)

    response = OOIListView.as_view()(request, organization_code=organization.code)

    assert response.status_code == 403


def test_update_scan_profiles_no_indemnification(rf, superuser_member, organization, mock_organization_view_octopoes):
    kwargs = {"organization_code": organization.code}
    url = reverse("ooi_list", kwargs=kwargs)

    request = rf.post(
        url,
        data={
            "ooi": ["Network|internet", "Hostname|internet|scanme.org."],
            "scan-profile": "L1",
            "action": "update-scan-profile",
        },
    )

    Indemnification.objects.get(user=superuser_member.user).delete()

    setup_request(request, superuser_member.user)

    response = OOIListView.as_view()(request, organization_code=organization.code)

    assert response.status_code == 403


def test_update_scan_profiles_octopoes_down(rf, superuser_member, organization, mock_organization_view_octopoes):
    mock_organization_view_octopoes().save_scan_profile.side_effect = ConnectionError
    superuser_member.trusted_clearance_level = 2
    superuser_member.acknowledged_clearance_level = 2
    superuser_member.save()
    request = rf.post(
        "ooi_list",
        data={
            "ooi": ["Network|internet", "Hostname|internet|scanme.org."],
            "scan-profile": "L2",
            "action": "update-scan-profile",
        },
    )

    setup_request(request, superuser_member.user)

    response = OOIListView.as_view()(request, organization_code=organization.code)

    assert response.status_code == 500


def test_update_scan_profiles_object_not_found(rf, superuser_member, organization, mock_organization_view_octopoes):
    mock_organization_view_octopoes().save_scan_profile.side_effect = ObjectNotFoundException("gone")
    superuser_member.trusted_clearance_level = 2
    superuser_member.acknowledged_clearance_level = 2
    superuser_member.save()

    request = rf.post(
        "ooi_list",
        data={
            "ooi": ["Network|internet", "Hostname|internet|scanme.org."],
            "scan-profile": "L2",
            "action": "update-scan-profile",
        },
    )

    setup_request(request, superuser_member.user)

    response = OOIListView.as_view()(request, organization_code=organization.code)

    assert response.status_code == 404


def test_delete_octopoes_down(rf, superuser_member, organization, mock_organization_view_octopoes):
    mock_organization_view_octopoes().delete.side_effect = ConnectionError

    request = rf.post(
        "ooi_list",
        data={
            "ooi": ["Network|internet", "Hostname|internet|scanme.org."],
            "scan-profile": "L2",
            "action": "delete",
        },
    )
    superuser_member.trusted_clearance_level = 4
    superuser_member.acknowledged_clearance_level = 4
    superuser_member.save()
    setup_request(request, superuser_member.user)

    response = OOIListView.as_view()(request, organization_code=organization.code)

    assert response.status_code == 500


def test_delete_object_not_found(rf, superuser_member, organization, mock_organization_view_octopoes):
    mock_organization_view_octopoes().delete.side_effect = ObjectNotFoundException("gone")

    request = rf.post(
        "ooi_list",
        data={
            "ooi": ["Network|internet", "Hostname|internet|scanme.org."],
            "scan-profile": "L2",
            "action": "delete",
        },
    )

    setup_request(request, superuser_member.user)

    response = OOIListView.as_view()(request, organization_code=organization.code)

    assert response.status_code == 404


def test_ooi_list_export_json(rf, superuser_member, organization, mock_organization_view_octopoes):
    kwargs = {"organization_code": organization.code}
    url = reverse("ooi_list_export", kwargs=kwargs)
    request = rf.get(url, {"file_type": "json"})
    request.resolver_match = resolve(url)

    setup_request(request, superuser_member.user)

    mock_organization_view_octopoes().list.return_value = Paginated[OOIType](
        count=200, items=[Network(name="testnetwork")] * 150
    )

    response = OOIListExportView.as_view()(request, organization_code=organization.code)

    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"
    assert mock_organization_view_octopoes().list.call_count == 3

    exported_objects = json.loads(response.content.decode())
    assert len(exported_objects) == 151
    assert "observed_at" in exported_objects[0]
    assert "filters" in exported_objects[0]

    assert exported_objects[1] == {"key": "Network|testnetwork", "name": "testnetwork", "ooi_type": "Network"}
    assert exported_objects[2] == {"key": "Network|testnetwork", "name": "testnetwork", "ooi_type": "Network"}


def test_ooi_list_export_csv(rf, superuser_member, organization, mock_organization_view_octopoes):
    kwargs = {"organization_code": organization.code}
    url = reverse("ooi_list_export", kwargs=kwargs)
    request = rf.get(url, {"file_type": "csv"})
    request.resolver_match = resolve(url)

    setup_request(request, superuser_member.user)

    mock_organization_view_octopoes().list.return_value = Paginated[OOIType](
        count=200, items=[Network(name="testnetwork")] * 150
    )

    response = OOIListExportView.as_view()(request, organization_code=organization.code)

    assert response.status_code == 200
    assert response.headers["Content-Type"] == "text/csv"
    assert mock_organization_view_octopoes().list.call_count == 3

    exported_objects = list(csv.DictReader(io.StringIO(response.content.decode()), delimiter=",", quotechar='"'))

    assert len(exported_objects) == 152
    assert "observed_at" in exported_objects[0]
    assert "filters" in exported_objects[0]
