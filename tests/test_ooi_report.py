from io import BytesIO
from unittest.mock import Mock

import pytest
from django.contrib.auth.models import Permission, ContentType
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.urls import reverse, resolve
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.middleware import OTPMiddleware
from octopoes.models.tree import ReferenceTree
from pytest_django.asserts import assertContains
from requests import HTTPError

from rocky.views import OOIReportView, OOIReportPDFView
from tools.models import OrganizationMember, OOIInformation


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


@pytest.fixture
def ooi_information() -> OOIInformation:
    data = {"description": "Fake description...", "recommendation": "Fake recommendation...", "risk": "Low"}
    ooi_information = OOIInformation.objects.create(id="KATFindingType|KAT-000", data=data, consult_api=False)
    return ooi_information


def setup_octopoes_mock() -> Mock:
    mock = Mock()
    mock.get_tree.return_value = ReferenceTree.parse_obj(
        {
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
    )
    return mock


def setup_request(request, user, active_organization, mocker):
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


def test_ooi_report(rf, my_user, organization, ooi_information, mocker):
    request = rf.get(reverse("ooi_report"), {"ooi_id": "Finding|Network|testnetwork|KAT-000"})
    request.resolver_match = resolve("/objects/report/")

    setup_request(request, my_user, organization, mocker)

    response = OOIReportView.as_view()(request)

    assert response.status_code == 200
    assertContains(response, "testnetwork")
    assertContains(response, "Fake description...")
    assertContains(response, "Fake recommendation...")


def test_ooi_pdf_report(rf, my_user, organization, ooi_information, mocker):
    request = rf.get(reverse("ooi_pdf_report"), {"ooi_id": "Finding|Network|testnetwork|KAT-000"})
    request.resolver_match = resolve("/objects/report/pdf/")

    setup_request(request, my_user, organization, mocker)

    # Setup Keiko mock
    mock_keiko_client = mocker.patch("rocky.views.ooi_report.keiko_client")
    mock_keiko_client.generate_report.return_value = "fake_report_id"
    mock_keiko_client.get_report.return_value = BytesIO(b"fake_binary_pdf_content")

    response = OOIReportPDFView.as_view()(request)

    assert response.status_code == 200
    assert response.getvalue() == b"fake_binary_pdf_content"

    report_data_param = mock_keiko_client.generate_report.call_args[0][1]
    # Verify that the data is sent correctly to Keiko
    assert report_data_param["meta"] == {
        "total": 1,
        "total_by_severity": {"critical": 0, "high": 0, "medium": 0, "low": 1, "recommendation": 0},
        "total_by_finding_type": {"KAT-000": 1},
        "total_finding_types": 1,
        "total_by_severity_per_finding_type": {"critical": 0, "high": 0, "medium": 0, "low": 1, "recommendation": 0},
    }
    assert report_data_param["findings_grouped"]["KAT-000"]["finding_type"]["id"] == "KAT-000"
    assert report_data_param["findings_grouped"]["KAT-000"]["list"][0]["description"] == "Fake description..."


def test_ooi_pdf_report_timeout(rf, my_user, organization, ooi_information, mocker):

    request = rf.get(reverse("ooi_pdf_report"), {"ooi_id": "Finding|Network|testnetwork|KAT-000"})
    request.resolver_match = resolve("/objects/report/pdf/")

    setup_request(request, my_user, organization, mocker)

    # Setup Keiko mock
    mock_keiko_client = mocker.patch("rocky.views.ooi_report.keiko_client")
    mock_keiko_client.generate_report.return_value = "fake_report_id"
    # Returns None when timeout is reached, but no report was generated
    mock_keiko_client.get_report.side_effect = HTTPError

    response = OOIReportPDFView.as_view()(request)

    assert response.status_code == 302
    assert response.url == reverse("ooi_report") + "?ooi_id=Finding%7CNetwork%7Ctestnetwork%7CKAT-000"
