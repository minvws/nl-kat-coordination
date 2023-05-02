from django.test import Client
from django.urls import reverse


def test_onboarding_redirect(rf, superuser):
    """
    Make a request through the Django middleware to see if we get redirected to
    the onboarding flow when logging in as superuser.
    """
    c = Client()
    login = c.force_login(superuser)
    print(login)
    response = c.get("/")
    print(response)
    assert response.status_code == 302
    assert response.headers["Location"] == reverse("step_introduction_registration")
