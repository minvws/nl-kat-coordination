from io import BytesIO

import pytest
from django.contrib.auth.models import Permission, ContentType
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.urls import reverse
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.middleware import OTPMiddleware

from rocky.views import UploadCSV
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
    permission, _ = Permission.objects.get_or_create(
        content_type=ContentType.objects.get_by_natural_key("tools", "organizationmember"),
        codename="can_scan_organization",
    )
    user.user_permissions.add(permission)

    device = user.staticdevice_set.create(name="default")
    device.token_set.create(token=user.get_username())

    return user


CSV_EXAMPLES = [
    # hostname
    b"name,network\nexample.com,internet",
    # hostname without network
    b"name\nexample.net",
    # ipv4s
    b"""address,network
1.1.1.1,internet
2.2.2.2,internet
3.3.3.3,darknet""",
    # ipv6s
    b"""address,network
FE80:CD00:0000:0CDE:1257:0000:211E:729C,internet
FE80:CD00:0000:0CDE:1257:0000:211E:729D,darknet""",
    # urls
    b"""network,raw
internet,https://example.com/
darknet,https://openkat.nl/""",
    # url withouth network
    b"raw\nhttps://example.com/",
]
INPUT_TYPES = ["Hostname", "Hostname", "IPAddressV4", "IPAddressV6", "URL", "URL"]
EXPECTED_OOI_COUNTS = [2, 2, 6, 4, 4, 2]


def test_upload_csv_page(rf, client, my_user, organization):
    request = rf.get(reverse("upload_csv"))
    request.user = my_user
    request.active_organization = organization

    response = UploadCSV.as_view()(request)
    assert response.status_code == 200


def test_upload_csv_simple(rf, client, my_user, organization):
    request = rf.get(reverse("upload_csv"))
    request.user = my_user
    request.active_organization = organization

    request = SessionMiddleware(lambda r: r)(request)
    request.session[DEVICE_ID_SESSION_KEY] = my_user.staticdevice_set.get().persistent_id
    request = OTPMiddleware(lambda r: r)(request)
    response = UploadCSV.as_view()(request)

    assert response.status_code == 200


def test_upload_bad_input(rf, client, my_user, organization, mocker):
    mocker.patch("rocky.views.upload_csv.save_ooi")

    example_file = BytesIO(b"invalid|'\n4\bcsv|format")
    example_file.name = "networks.csv"

    request = rf.post(reverse("upload_csv"), {"object_type": "Hostname", "csv_file": example_file})
    request.user = my_user
    request.active_organization = organization

    request = SessionMiddleware(lambda r: r)(request)
    request.session[DEVICE_ID_SESSION_KEY] = my_user.staticdevice_set.get().persistent_id
    request = OTPMiddleware(lambda r: r)(request)
    request = MessageMiddleware(lambda r: r)(request)
    response = UploadCSV.as_view()(request)

    assert response.status_code == 302

    messages = list(request._messages)
    assert "could not be created for row number" in messages[0].message


@pytest.mark.parametrize(
    "example_input, input_type, expected_ooi_counts", zip(CSV_EXAMPLES, INPUT_TYPES, EXPECTED_OOI_COUNTS)
)
def test_upload_csv(rf, client, my_user, organization, mocker, example_input, input_type, expected_ooi_counts):
    mock_save_ooi = mocker.patch("rocky.views.upload_csv.save_ooi")

    example_file = BytesIO(example_input)
    example_file.name = f"{input_type}.csv"

    request = rf.post(reverse("upload_csv"), {"object_type": input_type, "csv_file": example_file})
    request.user = my_user
    request.active_organization = organization

    request = SessionMiddleware(lambda r: r)(request)
    request.session[DEVICE_ID_SESSION_KEY] = my_user.staticdevice_set.get().persistent_id
    request = OTPMiddleware(lambda r: r)(request)
    request = MessageMiddleware(lambda r: r)(request)
    response = UploadCSV.as_view()(request)

    assert response.status_code == 302
    assert mock_save_ooi.call_count == expected_ooi_counts

    messages = list(request._messages)
    assert "successfully added" in messages[0].message
