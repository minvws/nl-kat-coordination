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
