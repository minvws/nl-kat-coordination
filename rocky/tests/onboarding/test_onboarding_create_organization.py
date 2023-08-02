from django.urls import reverse
from onboarding.views import OnboardingOrganizationSetupView
from pytest_django.asserts import assertContains
from requests import HTTPError

from tests.conftest import setup_request


def test_onboarding_create_organization(rf, superuser_member, mock_models_katalogus):
    request = setup_request(
        rf.post("step_organization_setup", {"name": "Test Organization", "code": "test"}), superuser_member.user
    )
    mock_models_katalogus().organization_exists.return_value = False

    response = OnboardingOrganizationSetupView.as_view()(request)
    assert response.status_code == 200
    assertContains(response, "Test Organization")


def test_onboarding_create_organization_already_exist_katalogus(
    rf, superuser, mock_models_katalogus, mock_models_octopoes
):
    request = setup_request(
        rf.post("step_organization_setup", {"name": "Test Organization", "code": "test"}), superuser
    )

    mock_models_katalogus().organization_exists.return_value = True
    mock_models_katalogus().create_organization.side_effect = HTTPError()

    response = OnboardingOrganizationSetupView.as_view()(request)
    assert response.status_code == 302
    assert response.headers["Location"] == reverse("step_indemnification_setup", kwargs={"organization_code": "test"})
