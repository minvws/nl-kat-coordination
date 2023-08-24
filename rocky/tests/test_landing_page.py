from account.views import AccountView
from pytest_django.asserts import assertContains

from rocky.views.landing_page import LandingPageView
from tests.conftest import setup_request


def test_landing_page_redirect(rf, client_member):
    request = setup_request(rf.get("landing_page"), client_member.user)

    response = LandingPageView.as_view()(request)
    assert response.status_code == 302  # Redirects to crisis-room


def test_language_lang_attribute(rf, client_member, language):
    response = AccountView.as_view()(
        setup_request(rf.get("account_detail"), client_member.user), organization_code=client_member.organization.code
    )
    assert response.status_code == 200
    assertContains(response, '<html lang="' + language + '"')
