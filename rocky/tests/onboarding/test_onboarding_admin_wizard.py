import pytest
from django.core.exceptions import PermissionDenied
from onboarding.views import (
    OnboardingIntroductionRegistrationView,
    OnboardingOrganizationSetupView,
    OnboardingOrganizationUpdateView,
)

from tests.conftest import setup_request


def test_step_1_admin_onboarding_registration(rf, superuser_member, admin_member, redteam_member, client_member):
    """
    This onboarding is before an organization has been created and it is only visible for superusers.
    """
    response_superuser = OnboardingIntroductionRegistrationView.as_view()(
        setup_request(rf.get("step_introduction_registration"), superuser_member.user),
        organization_code=superuser_member.organization.code,
    )

    assert response_superuser.status_code == 200

    with pytest.raises(PermissionDenied):
        OnboardingIntroductionRegistrationView.as_view()(
            setup_request(rf.get("step_introduction_registration"), admin_member.user),
            organization_code=admin_member.organization.code,
        )

    with pytest.raises(PermissionDenied):
        OnboardingIntroductionRegistrationView.as_view()(
            setup_request(rf.get("step_introduction_registration"), redteam_member.user),
            organization_code=redteam_member.organization.code,
        )

    with pytest.raises(PermissionDenied):
        OnboardingIntroductionRegistrationView.as_view()(
            setup_request(rf.get("step_introduction_registration"), client_member.user),
            organization_code=client_member.organization.code,
        )


def test_step_2a_onboarding_organization_setup(rf, superuser, adminuser, redteamuser, clientuser):
    response_superuser = OnboardingOrganizationSetupView.as_view()(
        setup_request(rf.get("step_2a_organization_setup"), superuser)
    )

    # Only superusers can create organizations
    assert response_superuser.status_code == 200

    with pytest.raises(PermissionDenied):
        OnboardingOrganizationSetupView.as_view()(setup_request(rf.get("step_2a_organization_setup"), adminuser))

    with pytest.raises(PermissionDenied):
        OnboardingOrganizationSetupView.as_view()(setup_request(rf.get("step_2a_organization_setup"), redteamuser))

    with pytest.raises(PermissionDenied):
        OnboardingOrganizationSetupView.as_view()(setup_request(rf.get("step_2a_organization_setup"), clientuser))


def test_step_2b_onboarding_organization_update(rf, superuser_member, admin_member, redteam_member, client_member):
    response_superuser = OnboardingOrganizationUpdateView.as_view()(
        setup_request(rf.get("step_2b_organization_setup"), superuser_member.user),
        organization_code=superuser_member.organization.code,
    )
    response_admin = OnboardingOrganizationUpdateView.as_view()(
        setup_request(rf.get("step_2b_organization_setup"), admin_member.user),
        organization_code=admin_member.organization.code,
    )

    # Only superusers and admins can update/edt/change organizations
    assert response_superuser.status_code == 200
    assert response_admin.status_code == 200

    with pytest.raises(PermissionDenied):
        OnboardingOrganizationUpdateView.as_view()(
            setup_request(rf.get("step_2b_organization_setup"), redteam_member.user),
            organization_code=redteam_member.organization.code,
        )

    with pytest.raises(PermissionDenied):
        OnboardingOrganizationUpdateView.as_view()(
            setup_request(rf.get("step_2b_organization_setup"), client_member.user),
            organization_code=client_member.organization.code,
        )
