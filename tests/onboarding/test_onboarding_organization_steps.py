import pytest
from pytest_django.asserts import assertContains, assertNotContains

from onboarding.views import (
    OnboardingAcknowledgeClearanceLevelView,
    OnboardingClearanceLevelIntroductionView,
    OnboardingIntroductionView,
)
from plugins.models import Plugin
from tests.conftest import setup_request


@pytest.mark.django_db(databases=["xtdb", "default"])
@pytest.mark.parametrize("member", ["superuser_member", "admin_member", "redteam_member", "client_member"])
def test_onboarding_introduction(request, member, rf):
    member = request.getfixturevalue(member)
    response = OnboardingIntroductionView.as_view()(
        setup_request(rf.get("step_introduction"), member.user), organization_code=member.organization.code
    )

    assert response.status_code == 200
    assertContains(response, "Welcome to OpenKAT")
    assertContains(response, "Skip onboarding")
    assertContains(response, "Let's get started")


def test_onboarding_clearance_level_introduction(rf, redteam_member, hostname):
    Plugin.objects.create(plugin_id="fierce", name="Fierce")
    response = OnboardingClearanceLevelIntroductionView.as_view()(
        setup_request(rf.get("step_clearance_level_introduction", {"ooi": hostname.pk}), redteam_member.user),
        organization_code=redteam_member.organization.code,
    )

    assert response.status_code == 200
    assertContains(response, "OpenKAT introduction")
    # TODO: fix
    # assertContains(response, "Object clearance for " + hostname.name)
    assertContains(response, "Introduction")
    assertContains(response, "How to know required clearance level")
    # assertContains(response, "Fierce")
    # assertContains(response, "DNS-Zone")
    assertContains(response, "Skip onboarding")
    assertContains(response, "Continue")

    assertNotContains(response, '<div class="action-buttons">', html=True)


def test_onboarding_acknowledge_clearance_level(rf, redteam_member, hostname):
    response = OnboardingAcknowledgeClearanceLevelView.as_view()(
        setup_request(rf.get("step_acknowledge_clearance_level", {"ooi": hostname.pk}), redteam_member.user),
        organization_code=redteam_member.organization.code,
    )

    assert response.status_code == 200
    assertContains(response, "OpenKAT introduction")
    # assertContains(response, "Setup scan - Object clearance for " + hostname.name)
    assertContains(response, "Trusted clearance level")
    assertContains(response, "Acknowledge clearance level")
    assertContains(response, "What is my clearance level?")
    assertContains(
        response,
        "Your administrator has <strong>trusted</strong> you with a clearance level of <strong>L"
        + str(redteam_member.trusted_clearance_level)
        + "</strong>.",
    )
    (
        "You have also <strong>acknowledged</strong> to use this clearance level of <strong>L"
        + str(redteam_member.acknowledged_clearance_level)
        + "</strong>."
    )

    redteam_member.trusted_clearance_level = 2
    redteam_member.acknowledged_clearance_level = -1
    redteam_member.save()

    response_accept = OnboardingAcknowledgeClearanceLevelView.as_view()(
        setup_request(rf.get("step_acknowledge_clearance_level", {"ooi": hostname.pk}), redteam_member.user),
        organization_code=redteam_member.organization.code,
    )

    assertContains(
        response_accept,
        "Your administrator has trusted you with a clearance level of <strong>L"
        + str(redteam_member.trusted_clearance_level)
        + "</strong>.",
    )
    assertContains(response_accept, "You must first accept this clearance level to continue.")


@pytest.mark.parametrize("clearance_level", [-1, 0])
def test_onboarding_acknowledge_clearance_level_no_clearance(rf, redteam_member, clearance_level, hostname):
    response = OnboardingAcknowledgeClearanceLevelView.as_view()(
        setup_request(rf.get("step_acknowledge_clearance_level", {"ooi": hostname.pk}), redteam_member.user),
        organization_code=redteam_member.organization.code,
    )

    assert response.status_code == 200
    redteam_member.trusted_clearance_level = clearance_level
    redteam_member.acknowledged_clearance_level = clearance_level
    redteam_member.save()

    response = OnboardingAcknowledgeClearanceLevelView.as_view()(
        setup_request(rf.get("step_acknowledge_clearance_level", {"ooi": hostname.pk}), redteam_member.user),
        organization_code=redteam_member.organization.code,
    )
    assertContains(response, "Unfortunately you cannot continue the onboarding.")
    assertContains(
        response,
        "Your administrator has trusted you with a clearance level of <strong>L" + str(clearance_level) + "</strong>.",
    )
    # assertContains(
    #     response,
    #     "You need at least a clearance level of <strong>L"
    #     + str(DNS_REPORT_LEAST_CLEARANCE_LEVEL)
    #     + "</strong> to scan <strong>"
    #     + str(hostname.pk)
    #     + "</strong>",
    # )
    assertContains(response, "Contact your administrator to receive a higher clearance.")

    assertContains(response, "Skip onboarding")
