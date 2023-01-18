from django.urls import reverse, resolve
from pytest_django.asserts import assertContains
from requests import HTTPError

from onboarding.views import OnboardingOrganizationSetupView
from tests.conftest import setup_request


def test_onboarding_create_organization(rf, my_user, mock_models_katalogus, mock_models_octopoes):
    url = reverse("step_organization_setup")
    request = rf.post(url, {"name": "Test Organization", "code": "test"})
    request.resolver_match = resolve(url)

    setup_request(request, my_user)

    mock_models_katalogus().organization_exists.return_value = False

    response = OnboardingOrganizationSetupView.as_view()(request)
    assert response.status_code == 200
    assertContains(response, "Test Organization")


def test_onboarding_create_organization_already_exist_katalogus(rf, user, mock_models_katalogus, mock_models_octopoes):
    url = reverse("step_organization_setup")
    request = rf.post(url, {"name": "Test Organization", "code": "test"})
    request.resolver_match = resolve(url)

    setup_request(request, user)

    mock_models_katalogus().organization_exists.return_value = True
    mock_models_katalogus().create_organization.side_effect = HTTPError()

    response = OnboardingOrganizationSetupView.as_view()(request)
    assert response.status_code == 302
    assert response.headers["Location"] == reverse("step_indemnification_setup", kwargs={"organization_code": "test"})
