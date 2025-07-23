from pytest_django.asserts import assertContains

from openkat.views.privacy_statement import PrivacyStatementView
from tests.conftest import setup_request


def test_privacy_statement(rf, client_member):
    request = setup_request(rf.get("privacy_statement"), client_member.user)

    response = PrivacyStatementView.as_view()(request)
    assert response.status_code == 200
    assertContains(response, "KAT Privacy Statement")
