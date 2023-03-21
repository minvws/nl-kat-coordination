from rocky.views.landing_page import LandingPageView
from tests.conftest import setup_request


def test_landing_page_redirect(rf, my_user, organization):
    request = setup_request(rf.get("landing_page"), my_user)

    response = LandingPageView.as_view()(request)
    assert response.status_code == 302  # Redirects to crisis-room
