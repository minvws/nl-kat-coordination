from io import BytesIO

import pytest
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.urls import reverse
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.middleware import OTPMiddleware

from rocky.views.upload_csv import UploadCSV
from tests.conftest import setup_request

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


def test_upload_csv_page(rf, my_user, organization):
    kwargs = {"organization_code": organization.code}
    request = rf.get(reverse("upload_csv", kwargs=kwargs))
    request.user = my_user
    request.organization = organization

    response = UploadCSV.as_view()(request, **kwargs)
    assert response.status_code == 200


def test_upload_csv_simple(rf, my_user, organization):
    kwargs = {"organization_code": organization.code}
    request = rf.get(reverse("upload_csv", kwargs=kwargs))
    request.user = my_user
    request.organization = organization

    request = SessionMiddleware(lambda r: r)(request)
    request.session[DEVICE_ID_SESSION_KEY] = my_user.staticdevice_set.get().persistent_id
    request = OTPMiddleware(lambda r: r)(request)
    response = UploadCSV.as_view()(request, **kwargs)

    assert response.status_code == 200


def test_upload_bad_input(rf, my_user, organization, mock_organization_view_octopoes):
    example_file = BytesIO(b"invalid|'\n4\bcsv|format")
    example_file.name = "networks.csv"

    kwargs = {"organization_code": organization.code}
    request = rf.post(
        reverse("upload_csv", kwargs=kwargs),
        {"object_type": "Hostname", "csv_file": example_file},
    )

    setup_request(request, my_user)

    response = UploadCSV.as_view()(request, **kwargs)

    assert response.status_code == 302

    messages = list(request._messages)
    assert "could not be created for row number" in messages[0].message


@pytest.mark.parametrize(
    "example_input, input_type, expected_ooi_counts",
    zip(CSV_EXAMPLES, INPUT_TYPES, EXPECTED_OOI_COUNTS),
)
def test_upload_csv(
    rf, my_user, mock_organization_view_octopoes, organization, example_input, input_type, expected_ooi_counts
):
    example_file = BytesIO(example_input)
    example_file.name = f"{input_type}.csv"

    kwargs = {"organization_code": organization.code}
    request = rf.post(
        reverse("upload_csv", kwargs=kwargs),
        {"object_type": input_type, "csv_file": example_file},
    )
    request.user = my_user
    request.organization = organization

    request = SessionMiddleware(lambda r: r)(request)
    request.session[DEVICE_ID_SESSION_KEY] = my_user.staticdevice_set.get().persistent_id
    request = OTPMiddleware(lambda r: r)(request)
    request = MessageMiddleware(lambda r: r)(request)
    response = UploadCSV.as_view()(request, **kwargs)

    assert response.status_code == 302
    assert mock_organization_view_octopoes().save_declaration.call_count == expected_ooi_counts

    messages = list(request._messages)
    assert "successfully added" in messages[0].message
