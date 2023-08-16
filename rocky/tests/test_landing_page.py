import pytest
from account.views import AccountView
from django.conf import settings
from django.utils.translation import activate, deactivate
from pytest_django.asserts import assertContains

from rocky.views.landing_page import LandingPageView
from tests.conftest import setup_request


def test_landing_page_redirect(rf, client_member):
    request = setup_request(rf.get("landing_page"), client_member.user)

    response = LandingPageView.as_view()(request)
    assert response.status_code == 302  # Redirects to crisis-room


LANG_LIST = [lang[0] for lang in settings.LANGUAGES]


@pytest.mark.parametrize("language", LANG_LIST)
def test_language_lang_attribute(rf, client_member, language):
    activate(language)

    response = AccountView.as_view()(
        setup_request(rf.get("account_detail"), client_member.user), organization_code=client_member.organization.code
    )
    assert response.status_code == 200
    assertContains(response, '<html lang="' + language + '"')
    deactivate()  # must decativate otherwise further tests fail to fetch context in English
