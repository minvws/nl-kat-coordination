from pytest_django.asserts import assertContains

from onboarding.views import OnboardingOrganizationSetupView
from tests.conftest import setup_request


def test_onboarding_create_organization(rf, superuser_member):
    request = setup_request(
        rf.post("step_organization_setup", {"name": "Test Organization", "code": "test"}), superuser_member.user
    )
    response = OnboardingOrganizationSetupView.as_view()(request)
    assert response.status_code == 200
    assertContains(response, "Test Organization")
