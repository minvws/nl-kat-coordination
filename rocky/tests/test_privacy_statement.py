from pytest_django.asserts import assertContains

from rocky.views.privacy_statement import PrivacyStatementView
from tests.conftest import setup_request


def test_privacy_statement(rf, my_user, organization):
    request = setup_request(rf.get("privacy_statement"), my_user)

    response = PrivacyStatementView.as_view()(request)
    assert response.status_code == 200
    assertContains(response, "KAT Privacy Statement")
