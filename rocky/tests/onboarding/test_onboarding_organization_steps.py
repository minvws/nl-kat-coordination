import pytest
from django.core.exceptions import PermissionDenied
from onboarding.views import (
    OnboardingChooseReportInfoView,
    OnboardingChooseReportTypeView,
    OnboardingIntroductionView,
    OnboardingReportView,
    OnboardingSetClearanceLevelView,
    OnboardingSetupScanOOIAddView,
    OnboardingSetupScanOOIDetailView,
    OnboardingSetupScanOOIInfoView,
    OnboardingSetupScanSelectPluginsView,
)
from pytest_django.asserts import assertContains
from tools.view_helpers import get_ooi_url

from tests.conftest import setup_request


@pytest.mark.parametrize("member", ["superuser_member", "admin_member", "redteam_member", "client_member"])
def test_onboarding_introduction(request, member, rf):
    member = request.getfixturevalue(member)
    response = OnboardingIntroductionView.as_view()(
        setup_request(rf.get("step_introduction"), member.user),
        organization_code=member.organization.code,
    )

    assert response.status_code == 200
    assertContains(response, "Welcome to OpenKAT")
    assertContains(response, "Skip onboarding")
    assertContains(response, "Let's get started")


@pytest.mark.parametrize("member", ["superuser_member", "admin_member", "redteam_member", "client_member"])
def test_onboarding_choose_report_info(request, member, rf):
    member = request.getfixturevalue(member)
    response = OnboardingChooseReportInfoView.as_view()(
        setup_request(rf.get("step_choose_report_info"), member.user),
        organization_code=member.organization.code,
    )

    assert response.status_code == 200

    assertContains(response, "KAT introduction")
    assertContains(response, "Reports")
    assertContains(response, "Data")
    assertContains(response, "Skip onboarding")
    assertContains(response, "Let's choose a report")


@pytest.mark.parametrize("member", ["superuser_member", "admin_member", "redteam_member", "client_member"])
def test_onboarding_choose_report_type(request, member, rf):
    member = request.getfixturevalue(member)
    response = OnboardingChooseReportTypeView.as_view()(
        setup_request(rf.get("step_choose_report_type"), member.user),
        organization_code=member.organization.code,
    )

    assert response.status_code == 200
    assertContains(response, "KAT introduction")
    assertContains(response, "Choose a report - Type")
    assertContains(response, "Skip onboarding")
    assertContains(response, "DNS report")
    assertContains(response, "Pen test")
    assertContains(response, "Mail report")
    assertContains(response, "DigiD")


@pytest.mark.parametrize("member", ["superuser_member", "admin_member", "redteam_member", "client_member"])
def test_onboarding_setup_scan(request, member, rf):
    member = request.getfixturevalue(member)
    response = OnboardingSetupScanOOIInfoView.as_view()(
        setup_request(rf.get("step_setup_scan_ooi_info"), member.user),
        organization_code=member.organization.code,
    )

    assert response.status_code == 200

    assertContains(response, "KAT introduction")
    assertContains(response, "Setup scan")
    assertContains(response, "Let OpenKAT know what object to scan")
    assertContains(response, "Understanding objects")
    assertContains(response, "Skip onboarding")
    assertContains(response, "Add URL")


@pytest.mark.parametrize("member", ["superuser_member", "admin_member", "redteam_member", "client_member"])
def test_onboarding_setup_scan_detail(request, member, rf, mock_organization_view_octopoes, network):
    mock_organization_view_octopoes().get.return_value = network
    member = request.getfixturevalue(member)
    response = OnboardingSetupScanOOIAddView.as_view()(
        setup_request(rf.get("step_setup_scan_ooi_add"), member.user),
        ooi_type="Network",
        organization_code=member.organization.code,
    )

    assert response.status_code == 200

    assertContains(response, "KAT introduction")
    assertContains(response, "Setup scan")
    assertContains(response, "Creating an object")
    assertContains(response, "Dependencies")
    assertContains(response, "Create object")
    assertContains(response, "Skip onboarding")


@pytest.mark.parametrize("member", ["superuser_member", "admin_member", "redteam_member", "client_member"])
def test_onboarding_setup_scan_detail_create_ooi(
    request, member, rf, mock_organization_view_octopoes, network, mock_bytes_client
):
    mock_organization_view_octopoes().get.return_value = network
    member = request.getfixturevalue(member)

    response = OnboardingSetupScanOOIAddView.as_view()(
        setup_request(
            rf.post(
                "step_setup_scan_ooi_add", {"network": "Network|internet", "raw": "http://example.org", "web_url": ""}
            ),
            member.user,
        ),
        ooi_type="URL",
        organization_code=member.organization.code,
    )

    assert response.status_code == 302
    assert response.headers["Location"] == get_ooi_url(
        "step_set_clearance_level", "URL|internet|http://example.org", member.organization.code
    )


def test_onboarding_set_clearance_level(
    rf, superuser_member, admin_member, redteam_member, client_member, mock_organization_view_octopoes, network
):
    mock_organization_view_octopoes().get.return_value = network
    ooi_id = "Network|internet"

    response_superuser = OnboardingSetClearanceLevelView.as_view()(
        setup_request(rf.get("step_set_clearance_level", {"ooi_id": ooi_id}), superuser_member.user),
        organization_code=superuser_member.organization.code,
    )
    response_redteam = OnboardingSetClearanceLevelView.as_view()(
        setup_request(rf.get("step_set_clearance_level", {"ooi_id": ooi_id}), redteam_member.user),
        organization_code=redteam_member.organization.code,
    )

    assert response_redteam.status_code == 200
    assert response_superuser.status_code == 200

    assertContains(response_redteam, "OpenKAT introduction")
    assertContains(response_redteam, "Set clearance level for " + ooi_id)
    assertContains(response_redteam, "How to know required clearance level")
    assertContains(response_redteam, "Set clearance level")
    assertContains(response_redteam, "Skip onboarding")

    with pytest.raises(PermissionDenied):
        OnboardingSetClearanceLevelView.as_view()(
            setup_request(rf.get("step_set_clearance_level", {"ooi_id": ooi_id}), admin_member.user),
            organization_code=admin_member.organization.code,
        )
    with pytest.raises(PermissionDenied):
        OnboardingSetClearanceLevelView.as_view()(
            setup_request(rf.get("step_set_clearance_level", {"ooi_id": ooi_id}), client_member.user),
            organization_code=client_member.organization.code,
        )


@pytest.mark.parametrize("member", ["superuser_member", "redteam_member"])
def test_onboarding_select_plugins(
    request,
    member,
    rf,
    mock_views_katalogus,
    mock_organization_view_octopoes,
    network,
):
    mock_organization_view_octopoes().get.return_value = network
    member = request.getfixturevalue(member)
    request = setup_request(rf.get("step_setup_scan_select_plugins", {"ooi_id": "Network|internet"}), member.user)

    request.session["clearance_level"] = "2"

    response = OnboardingSetupScanSelectPluginsView.as_view()(request, organization_code=member.organization.code)

    assert response.status_code == 200

    assertContains(response, "Setup scan - Enable plugins")
    assertContains(response, "Plugins introduction")
    assertContains(response, "Boefjes")
    assertContains(response, "Normalizers")
    assertContains(response, "Bits")
    assertContains(response, "Suggested plugins")
    assertContains(response, "Skip onboarding")
    assertContains(response, "Enable and start scan")


@pytest.mark.parametrize("member", ["admin_member", "client_member"])
def test_onboarding_select_plugins_perms(
    request,
    member,
    rf,
    mock_views_katalogus,
    mock_organization_view_octopoes,
    network,
):
    mock_organization_view_octopoes().get.return_value = network
    member = request.getfixturevalue(member)
    request = setup_request(rf.get("step_setup_scan_select_plugins", {"ooi_id": "Network|internet"}), member.user)

    request.session["clearance_level"] = "2"
    with pytest.raises(PermissionDenied):
        OnboardingSetupScanSelectPluginsView.as_view()(request, organization_code=member.organization.code)


@pytest.mark.parametrize("member", ["superuser_member", "admin_member", "redteam_member", "client_member"])
def test_onboarding_ooi_detail_scan(request, member, rf, mock_organization_view_octopoes, network):
    mock_organization_view_octopoes().get.return_value = network
    member = request.getfixturevalue(member)
    request = setup_request(rf.get("step_setup_scan_ooi_detail", {"ooi_id": "Network|internet"}), member.user)
    request.session["clearance_level"] = "2"

    response = OnboardingSetupScanOOIDetailView.as_view()(request, organization_code=member.organization.code)

    assert response.status_code == 200

    assertContains(response, "KAT introduction")
    assertContains(response, "Setup scan")
    assertContains(response, "Creating an object")
    assertContains(response, "Network")
    assertContains(response, "Skip onboarding")
    assertContains(response, "Start scanning")


@pytest.mark.parametrize("member", ["superuser_member", "admin_member", "redteam_member", "client_member"])
def test_onboarding_scanning_boefjes(request, member, rf, mock_organization_view_octopoes, network):
    mock_organization_view_octopoes().get.return_value = network
    member = request.getfixturevalue(member)
    response = OnboardingReportView.as_view()(
        setup_request(rf.get("step_report", {"ooi_id": "Network|internet"}), member.user),
        organization_code=member.organization.code,
    )

    assert response.status_code == 200

    assertContains(response, "KAT introduction")
    assertContains(response, "Report")
    assertContains(response, "Boefjes are scanning")
    assertContains(response, "Open my DNS-report")
