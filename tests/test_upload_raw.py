from datetime import datetime, timezone
from io import BytesIO

from pytest_django.asserts import assertContains

from files.models import File
from openkat.views.upload_raw import UploadRaw
from tests.conftest import setup_request


def test_upload_raw_page(rf, redteam_member, octopoes_api_connector):
    request = setup_request(rf.get("upload_raw"), redteam_member.user)

    response = UploadRaw.as_view()(request, organization_code=redteam_member.organization.code)
    assert response.status_code == 200
    assertContains(response, "Upload raw")


def test_upload_raw_simple(rf, redteam_member, octopoes_api_connector):
    request = setup_request(rf.get("upload_raw"), redteam_member.user)
    response = UploadRaw.as_view()(request, organization_code=redteam_member.organization.code)

    assert response.status_code == 200


def test_upload_empty(rf, redteam_member, network):
    example_file = BytesIO(b"")

    request = setup_request(
        rf.post(
            "upload_raw",
            {"type": "Hostname", "raw_file": example_file, "ooi_id": network, "date": datetime.now(timezone.utc)},
        ),
        redteam_member.user,
    )
    response = UploadRaw.as_view()(request, organization_code=redteam_member.organization.code)

    assert response.status_code == 200
    assert File.objects.count() == 0

    assertContains(response, "Required")


def test_upload_raw(rf, redteam_member, octopoes_api_connector, network):
    example_file = BytesIO(b"abc")
    example_file.name = "test"
    date = datetime.now(timezone.utc)

    request = setup_request(
        rf.post("upload_raw", {"type": "abc/def,ghi", "raw_file": example_file, "ooi_id": network, "date": date}),
        redteam_member.user,
    )
    response = UploadRaw.as_view()(request, organization_code=redteam_member.organization.code)
    assert response.status_code == 302

    assert File.objects.count() == 1
    assert File.objects.first().file.read() == b"abc"

    messages = list(request._messages)
    assert "successfully added" in messages[0].message
