from datetime import datetime, timezone

import pytest
from crisis_room.views import (
    CrisisRoomView,
    OrganizationFindingTypeCount,
    load_finding_type_risks,
)
from django.urls import resolve, reverse
from pytest_django.asserts import assertContains
from tools.models import OOIInformation
from tools.ooi_helpers import RiskLevelSeverity

from octopoes.models.pagination import Paginated
from octopoes.models.types import OOIType
from tests.conftest import setup_request


@pytest.fixture
def test_katfindingtype_information():
    OOIInformation.objects.create(
        id="KATFindingType|TestFindingType",
        data={
            "description": "The test KAT finding type",
            "impact": "A test impact",
            "recommendation": "Fix the finding",
            "source": "https://openkat.nl/",
            "risk": "Middle",
        },
    )


@pytest.fixture
def test_cvefindingtype_information():
    OOIInformation.objects.create(
        id="CVEFindingType|CVE-2020-1234",
        data={
            "cvss": 9,
            "description": "Test CVE description.",
            "information updated": "20-04-2023 12:47:29",
            "source": "https://openkat.nl/cve/CVE-2020-1234",
        },
    )


@pytest.fixture
def test_snykfindingtype_information():
    OOIInformation.objects.create(
        id="SnykFindingType|TestSnykFindingType",
        data={
            "affected versions": "[0,]",
            "description": "Test Snyk description",
            "information updated": "20-04-2023 13:10:46",
            "risk": "5.5",
            "source": "https://mispo.es/TestSnykFindingType",
        },
    )


@pytest.fixture
def retirejsfindingtype_information():
    OOIInformation.objects.create(
        id="RetireJSFindingType|RetireJS-test-f901",
        data={
            "description": "Test RetireJS description",
            "information updated": "20-04-2023 13:10:46",
            "severity": "medium",
            "source": "https://mispo.es/RetireJS-test-f901",
        },
    )


def test_load_finding_type_severities(
    db,
    django_assert_num_queries,
    test_katfindingtype_information,
    test_cvefindingtype_information,
    test_snykfindingtype_information,
    retirejsfindingtype_information,
):
    with django_assert_num_queries(1):
        assert load_finding_type_risks(
            {
                "KATFindingType|TestFindingType",
                "CVEFindingType|CVE-2020-1234",
                "SnykFindingType|TestSnykFindingType",
                "RetireJSFindingType|RetireJS-test-f901",
            }
        ) == {
            "KATFindingType|TestFindingType": RiskLevelSeverity.MEDIUM.value,
            "CVEFindingType|CVE-2020-1234": RiskLevelSeverity.CRITICAL.value,
            "SnykFindingType|TestSnykFindingType": RiskLevelSeverity.MEDIUM.value,
            "RetireJSFindingType|RetireJS-test-f901": RiskLevelSeverity.MEDIUM.value,
        }


def test_crisis_room(rf, client_member, mock_crisis_room_octopoes):
    request = setup_request(rf.get("crisis_room"), client_member.user)
    request.resolver_match = resolve(reverse("crisis_room"))

    mock_crisis_room_octopoes().get_finding_type_count.return_value = {
        "KATFindingType|TestFindingType": 1,
    }

    response = CrisisRoomView.as_view()(request)

    assert response.status_code == 200
    assertContains(response, "1")

    assert mock_crisis_room_octopoes().get_finding_type_count.call_count == 1


def test_crisis_room_observed_at(rf, client_member, mock_crisis_room_octopoes):
    mock_crisis_room_octopoes().list.return_value = Paginated[OOIType](count=0, items=[])

    request = setup_request(rf.get("crisis_room", {"observed_at": "2021-01-01"}), client_member.user)
    request.resolver_match = resolve(reverse("crisis_room"))
    response = CrisisRoomView.as_view()(request)
    assert response.status_code == 200
    assertContains(response, "Jan 01, 2021")

    request = setup_request(rf.get("crisis_room", {"observed_at": "2021-bad-format"}), client_member.user)
    request.resolver_match = resolve(reverse("crisis_room"))
    response = CrisisRoomView.as_view()(request)
    assert response.status_code == 200
    assertContains(response, datetime.now(timezone.utc).date().strftime("%b %d, %Y"))


def test_finding_type_count_total():
    assert OrganizationFindingTypeCount("dev", "_dev", {"test": 1, "CVE-2020-1234": 2}).total == 3
