from datetime import datetime, timezone

from crisis_room.views import (
    CrisisRoomView,
    OrganizationFindingCountPerSeverity,
)
from django.urls import resolve, reverse
from pytest_django.asserts import assertContains

from octopoes.connector import ConnectorException
from tests.conftest import setup_request


def test_crisis_room(rf, client_member, mock_crisis_room_octopoes):
    request = setup_request(rf.get("crisis_room"), client_member.user)
    request.resolver_match = resolve(reverse("crisis_room"))

    mock_crisis_room_octopoes().count_findings_by_severity.return_value = {
        "medium": 1,
        "critical": 0,
    }

    response = CrisisRoomView.as_view()(request)

    assert response.status_code == 200
    assertContains(response, '<a href="/en/test/findings/?severity=medium">1</a>', html=True)
    assertContains(response, '<td><span class="critical">Critical</span></td><td class="number">0</td>', html=True)

    assert mock_crisis_room_octopoes().count_findings_by_severity.call_count == 1


def test_crisis_room_observed_at(rf, client_member, mock_crisis_room_octopoes):
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


def test_org_finding_count_total():
    assert OrganizationFindingCountPerSeverity("dev", "_dev", {"medium": 1, "low": 2}).total == 3


def test_crisis_room_error(rf, client_user_two_organizations, mock_crisis_room_octopoes):
    request = setup_request(rf.get("crisis_room"), client_user_two_organizations)
    request.resolver_match = resolve(reverse("crisis_room"))

    mock_crisis_room_octopoes().count_findings_by_severity.side_effect = [
        {
            "medium": 1,
            "critical": 0,
        },
        ConnectorException("error"),
    ]

    response = CrisisRoomView.as_view()(request)

    assert response.status_code == 200
    assertContains(response, '<a href="/en/test/findings/?severity=medium">1</a>', html=True)
    assertContains(response, '<td><span class="critical">Critical</span></td><td class="number">0</td>', html=True)

    messages = list(request._messages)
    assert (
        messages[0].message
        == "Failed to get list of findings for organization org_b, check server logs for more details."
    )

    assert mock_crisis_room_octopoes().count_findings_by_severity.call_count == 2
