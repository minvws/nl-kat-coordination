from unittest.mock import MagicMock

from crisis_room.views import CrisisRoomFindings, CrisisRoomMixin

from tests.conftest import setup_request


def test_crisis_room_findings_dashboard(rf, mocker, client_member, findings_dashboard_mock_data):
    request = setup_request(rf.get("crisis_room_findings"), client_member.user)
    response = CrisisRoomFindings.as_view()(request)

    mixin = CrisisRoomMixin()
    mixin.get_organizations_findings = MagicMock(return_value=findings_dashboard_mock_data)

    print(response.__dict__)

    assert response.status_code == 302


def test_get_organizations_findings():
    """Test if the highest risk level is collected, only critical and high (maximum 25) finding types are returned."""


def test_collect_findings_dashboard():
    """Test if the method returns the right dict format. Only the most recent report should be visible in the dict."""


def test_get_organizations_findings_summary():
    """Test if the summary gives the right results. The finding_types and occurrences should be counted correctly."""


def test_get_user_organizations():
    """Test if the correct organizations are collected by the selected user."""
