from crisis_room.views import CrisisRoomFindings
from pytest_django.asserts import assertContains

from tests.conftest import setup_request


def test_crisis_room_findings_dashboard(rf, mocker, client_member, findings_dashboard_mock_data):
    dashboard_service = mocker.patch("crisis_room.views.DashboardService")()
    dashboard_service.collect_findings_dashboard.return_value = findings_dashboard_mock_data

    request = setup_request(rf.get("crisis_room_findings"), client_member.user)
    response = CrisisRoomFindings.as_view()(request)

    assert response.status_code == 200
    assertContains(response, client_member.organization)
    assertContains(response, '<td class="number">6</td>', html=True)
    assertContains(
        response,
        '<tr><td><span class="medium">Medium</span></td><td class="number">6</td><td class="number">6</td></tr>',
        html=True,
    )
    assertContains(
        response,
        '<tr><td><span class="low">Low</span></td><td class="number">2</td><td class="number">2</td></tr>',
        html=True,
    )
    assertContains(response, '<td><a href="/en/test/">Test Organization</a></td>', html=True)
    assertContains(response, "<td>4</td><td>4</td>", html=True)
    assertContains(response, '<td><span class="medium">Medium</span></td><td>0</td>', html=True)
    assertContains(response, "<td>0</td>", html=True)


def test_get_organizations_findings():
    """Test if the highest risk level is collected, only critical and high (maximum 25) finding types are returned."""


def test_collect_findings_dashboard():
    """Test if the method returns the right dict format. Only the most recent report should be visible in the dict."""


def test_get_user_organizations():
    """Test if the correct organizations are collected by the selected user."""
