from unittest.mock import Mock

import pytest
from django.contrib.auth.models import Permission, ContentType
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.urls import reverse, resolve
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.middleware import OTPMiddleware
from octopoes.models import ScanLevel
from octopoes.models.pagination import Paginated
from octopoes.models.types import OOIType, Network
from pytest_django.asserts import assertContains

from rocky.views import OOIListView
from tools.models import OrganizationMember


@pytest.fixture
def my_user(user, organization):
    OrganizationMember.objects.create(
        user=user,
        organization=organization,
        verified=True,
        authorized=True,
        status=OrganizationMember.STATUSES.ACTIVE,
        trusted_clearance_level=4,
        acknowledged_clearance_level=4,
    )
    content_type = ContentType.objects.get_by_natural_key("tools", "organizationmember")
    permission, _ = Permission.objects.get_or_create(
        content_type=content_type,
        codename="can_scan_organization",
    )
    user.user_permissions.add(permission)

    device = user.staticdevice_set.create(name="default")
    device.token_set.create(token=user.get_username())

    return user


def setup_octopoes_mock() -> Mock:
    mock = Mock()
    mock.list.return_value = Paginated[OOIType](count=1, items=[Network(name="testnetwork")])
    return mock


def setup_request(request, user, active_organization):
    """
    Setup request with middlewares, user, organization and octopoes
    """
    request = SessionMiddleware(lambda r: r)(request)
    request.session[DEVICE_ID_SESSION_KEY] = user.staticdevice_set.get().persistent_id
    request = OTPMiddleware(lambda r: r)(request)
    request = MessageMiddleware(lambda r: r)(request)

    request.user = user
    request.active_organization = active_organization

    request.octopoes_api_connector = setup_octopoes_mock()

    return request


def test_ooi_list(rf, my_user, organization):

    request = rf.get(reverse("ooi_list"))
    request.resolver_match = resolve("/objects/")

    request.user = my_user
    request.active_organization = organization

    setup_request(request, my_user, organization)

    response = OOIListView.as_view()(request)

    assert response.status_code == 200
    assert request.octopoes_api_connector.list.call_count == 2
    assertContains(response, "testnetwork")


def test_ooi_list_with_clearance_level_filter(rf, my_user, organization):
    request = rf.get(reverse("ooi_list"), {"clearance_level": [0, 1]})
    request.resolver_match = resolve("/objects/")

    request.user = my_user
    request.active_organization = organization

    setup_request(request, my_user, organization)

    response = OOIListView.as_view()(request)

    assert response.status_code == 200
    assert request.octopoes_api_connector.list.call_count == 2

    list_call_0 = request.octopoes_api_connector.list.call_args_list[0]
    assert list_call_0.kwargs["scan_level"] == {ScanLevel.L0, ScanLevel.L1}

    list_call_1 = request.octopoes_api_connector.list.call_args_list[1]
    assert list_call_1.kwargs["scan_level"] == {ScanLevel.L0, ScanLevel.L1}

    assertContains(response, "testnetwork")
