from django.urls import reverse, resolve
from pytest_django.asserts import assertContains

from octopoes.models import ScanLevel, ScanProfileType
from octopoes.models.ooi.network import Network
from octopoes.models.pagination import Paginated
from octopoes.models.types import OOIType
from rocky.views.ooi_list import OOIListView
from tests.conftest import setup_request
from tools.models import OrganizationMember


def test_ooi_list(rf, my_user, organization, mock_organization_view_octopoes):
    kwargs = {"organization_code": organization.code}
    url = reverse("ooi_list", kwargs=kwargs)
    request = rf.get(url)
    request.resolver_match = resolve(url)

    setup_request(request, my_user)

    mock_organization_view_octopoes().list.return_value = Paginated[OOIType](
        count=200, items=[Network(name="testnetwork")] * 150
    )

    response = OOIListView.as_view()(request, **kwargs)

    assert response.status_code == 200
    assert mock_organization_view_octopoes().list.call_count == 2
    assertContains(response, "testnetwork")


def test_ooi_list_with_clearance_type_filter_and_clearance_level_filter(
    rf, my_user, organization, mock_organization_view_octopoes
):
    kwargs = {"organization_code": organization.code}
    url = reverse("ooi_list", kwargs=kwargs)
    request = rf.get(
        url,
        {"clearance_level": [0, 1], "clearance_type": ["declared", "inherited"]},
    )
    request.resolver_match = resolve(url)

    setup_request(request, my_user)

    mock_organization_view_octopoes().list.return_value = Paginated[OOIType](
        count=200, items=[Network(name="testnetwork")] * 150
    )

    response = OOIListView.as_view()(request, **kwargs)

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


def test_ooi_list_delete_multiple(rf, my_user, organization, mock_organization_view_octopoes):
    kwargs = {"organization_code": organization.code}
    url = reverse("ooi_list", kwargs=kwargs)

    request = rf.post(
        url,
        data={
            "ooi": ["Network|internet", "Hostname|internet|scanme.org."],
            "scan-profile": "L0",
            "action": "delete",
        },
    )
    request.resolver_match = resolve(url)
    setup_request(request, my_user)

    my_user.acknowledged_clearance_level = 0
    my_user.save()
    response = OOIListView.as_view()(request, **kwargs)

    assert response.status_code == 200
    assert mock_organization_view_octopoes().list.call_count == 2
    assert mock_organization_view_octopoes().delete.call_count == 2


def test_update_scan_profile_multiple(rf, my_user, organization, mock_organization_view_octopoes):
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
    request.resolver_match = resolve(url)
    setup_request(request, my_user)
    response = OOIListView.as_view()(request, **kwargs)

    assert response.status_code == 200
    assert mock_organization_view_octopoes().save_scan_profile.call_count == 2


def test_update_scan_profile_single(rf, my_user, organization, mock_organization_view_octopoes):
    kwargs = {"organization_code": organization.code}
    url = reverse("ooi_list", kwargs=kwargs)

    request = rf.post(
        url,
        data={
            "ooi": ["Hostname|internet|scanme.org."],
            "scan-profile": "L4",
            "action": "update-scan-profile",
        },
    )
    request.resolver_match = resolve(url)
    setup_request(request, my_user)
    response = OOIListView.as_view()(request, **kwargs)

    assert response.status_code == 200
    assert mock_organization_view_octopoes().save_scan_profile.call_count == 1


def test_update_scan_profiles_forbidden_acknowledged(rf, my_user, organization, mock_organization_view_octopoes):
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
    request.resolver_match = resolve(url)

    member = OrganizationMember.objects.get(user=my_user)
    member.acknowledged_clearance_level = -1
    member.save()

    setup_request(request, my_user)

    response = OOIListView.as_view()(request, **kwargs)

    assert response.status_code == 403
    assert mock_organization_view_octopoes().save_scan_profile.call_count == 0


def test_update_scan_profiles_forbidden_trusted(rf, my_user, organization, mock_organization_view_octopoes):
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
    request.resolver_match = resolve(url)

    member = OrganizationMember.objects.get(user=my_user)
    member.trusted_clearance_level = -1
    member.save()

    setup_request(request, my_user)

    response = OOIListView.as_view()(request, **kwargs)

    assert response.status_code == 403
    assert mock_organization_view_octopoes().save_scan_profile.call_count == 0
