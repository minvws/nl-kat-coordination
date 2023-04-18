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

from tests.conftest import setup_request


def test_onboarding_introduction(rf, redteam_member):
    request = setup_request(rf.get("step_introduction"), redteam_member.user)
    response = OnboardingIntroductionView.as_view()(request, organization_code=redteam_member.organization.code)
    assert response.status_code == 200
    assertContains(response, "Welcome to OpenKAT")
    assertContains(response, "Skip onboarding")
    assertContains(response, "Let's get started")


def test_onboarding_choose_report_info(rf, redteam_member):
    request = setup_request(rf.get("step_choose_report_info"), redteam_member.user)
    response = OnboardingChooseReportInfoView.as_view()(request, organization_code=redteam_member.organization.code)
    assert response.status_code == 200
    assertContains(response, "KAT introduction")
    assertContains(response, "Reports")
    assertContains(response, "Data")
    assertContains(response, "Skip onboarding")
    assertContains(response, "Let's choose a report")


def test_onboarding_choose_report_type(rf, redteam_member):
    request = setup_request(rf.get("step_choose_report_type"), redteam_member.user)
    response = OnboardingChooseReportTypeView.as_view()(request, organization_code=redteam_member.organization.code)
    assert response.status_code == 200
    assertContains(response, "KAT introduction")
    assertContains(response, "Choose a report - Type")
    assertContains(response, "Skip onboarding")
    assertContains(response, "DNS report")
    assertContains(response, "Pen test")
    assertContains(response, "Mail report")
    assertContains(response, "DigiD")


def test_onboarding_setup_scan(rf, redteam_member):
    request = setup_request(rf.get("step_setup_scan_ooi_info"), redteam_member.user)
    response = OnboardingSetupScanOOIInfoView.as_view()(request, organization_code=redteam_member.organization.code)
    assert response.status_code == 200
    assertContains(response, "KAT introduction")
    assertContains(response, "Setup scan")
    assertContains(response, "Let OpenKAT know what object to scan")
    assertContains(response, "Understanding objects")
    assertContains(response, "Skip onboarding")
    assertContains(response, "Add URL")


def test_onboarding_setup_scan_detail(rf, redteam_member, mock_organization_view_octopoes, network):
    mock_organization_view_octopoes().get.return_value = network

    request = setup_request(rf.get("step_setup_scan_ooi_add"), redteam_member.user)
    response = OnboardingSetupScanOOIAddView.as_view()(
        request, ooi_type="Network", organization_code=redteam_member.organization.code
    )

    assert response.status_code == 200
    assertContains(response, "KAT introduction")
    assertContains(response, "Setup scan")
    assertContains(response, "Creating an object")
    assertContains(response, "Dependencies")
    assertContains(response, "Create object")
    assertContains(response, "Skip onboarding")


def test_onboarding_set_clearance_level(rf, redteam_member, mock_organization_view_octopoes, network):
    mock_organization_view_octopoes().get.return_value = network
    ooi_id = "Network|internet"
    request = setup_request(rf.get("step_set_clearance_level", {"ooi_id": ooi_id}), redteam_member.user)
    response = OnboardingSetClearanceLevelView.as_view()(request, organization_code=redteam_member.organization.code)

    assert response.status_code == 200
    assertContains(response, "OpenKAT introduction")
    assertContains(response, "Set clearance level for " + ooi_id)
    assertContains(response, "How to know required clearance level")
    assertContains(response, "Set clearance level")
    assertContains(response, "Skip onboarding")


def test_onboarding_select_plugins(rf, redteam_member, mock_views_katalogus, mock_organization_view_octopoes, network):
    mock_organization_view_octopoes().get.return_value = network

    request = setup_request(
        rf.get("step_setup_scan_select_plugins", {"ooi_id": "Network|internet"}), redteam_member.user
    )
    request.session["clearance_level"] = "2"
    response = OnboardingSetupScanSelectPluginsView.as_view()(
        request, organization_code=redteam_member.organization.code
    )

    assert response.status_code == 200
    assertContains(response, "Setup scan - Enable plugins")
    assertContains(response, "Plugins introduction")
    assertContains(response, "Boefjes")
    assertContains(response, "Normalizers")
    assertContains(response, "Bits")
    assertContains(response, "Suggested plugins")
    assertContains(response, "Skip onboarding")
    assertContains(response, "Enable and start scan")


def test_onboarding_ooi_detail_scan(rf, redteam_member, mock_organization_view_octopoes, network):
    mock_organization_view_octopoes().get.return_value = network

    request = setup_request(rf.get("step_setup_scan_ooi_detail", {"ooi_id": "Network|internet"}), redteam_member.user)
    request.session["clearance_level"] = "2"
    response = OnboardingSetupScanOOIDetailView.as_view()(request, organization_code=redteam_member.organization.code)

    assert response.status_code == 200
    assertContains(response, "KAT introduction")
    assertContains(response, "Setup scan")
    assertContains(response, "Creating an object")
    assertContains(response, "Network")
    assertContains(response, "Skip onboarding")
    assertContains(response, "Start scanning")


def test_onboarding_scanning_boefjes(rf, redteam_member, mock_organization_view_octopoes, network):
    mock_organization_view_octopoes().get.return_value = network

    request = setup_request(rf.get("step_report", {"ooi_id": "Network|internet"}), redteam_member.user)
    response = OnboardingReportView.as_view()(request, organization_code=redteam_member.organization.code)

    assert response.status_code == 200
    assertContains(response, "KAT introduction")
    assertContains(response, "Report")
    assertContains(response, "Boefjes are scanning")
    assertContains(response, "Open my DNS-report")
