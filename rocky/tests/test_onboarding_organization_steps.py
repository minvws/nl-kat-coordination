from pytest_django.asserts import assertContains

from onboarding.views import (
    OnboardingIntroductionView,
    OnboardingChooseReportInfoView,
    OnboardingChooseReportTypeView,
    OnboardingSetupScanOOIInfoView,
    OnboardingSetupScanOOIDetailView,
    OnboardingSetClearanceLevelView,
    OnboardingSetupScanSelectPluginsView,
    OnboardingSetupScanOOIAddView,
    OnboardingReportView,
)
from tests.conftest import setup_request


def test_onboarding_introduction(rf, my_red_teamer, organization, mock_models_katalogus, mock_models_octopoes):
    request = setup_request(rf.get("step_introduction"), my_red_teamer)
    response = OnboardingIntroductionView.as_view()(request, organization_code=organization.code)
    assert response.status_code == 200
    assertContains(response, "Welcome to OpenKAT")
    assertContains(response, "Skip onboarding")
    assertContains(response, "Let's get started")


def test_onboarding_choose_report_info(rf, my_red_teamer, organization, mock_models_katalogus, mock_models_octopoes):
    request = setup_request(rf.get("step_choose_report_info"), my_red_teamer)
    response = OnboardingChooseReportInfoView.as_view()(request, organization_code=organization.code)
    assert response.status_code == 200
    assertContains(response, "KAT introduction")
    assertContains(response, "Reports")
    assertContains(response, "Data")
    assertContains(response, "Skip onboarding")
    assertContains(response, "Let's choose a report")


def test_onboarding_choose_report_type(rf, my_red_teamer, organization, mock_models_katalogus, mock_models_octopoes):
    request = setup_request(rf.get("step_choose_report_type"), my_red_teamer)
    response = OnboardingChooseReportTypeView.as_view()(request, organization_code=organization.code)
    assert response.status_code == 200
    assertContains(response, "KAT introduction")
    assertContains(response, "Choose a report - Type")
    assertContains(response, "Skip onboarding")
    assertContains(response, "DNS report")
    assertContains(response, "Pen test")
    assertContains(response, "Mail report")
    assertContains(response, "DigiD")


def test_onboarding_setup_scan(rf, my_red_teamer, organization, mock_models_katalogus, mock_models_octopoes):
    request = setup_request(rf.get("step_setup_scan_ooi_info"), my_red_teamer)
    response = OnboardingSetupScanOOIInfoView.as_view()(request, organization_code=organization.code)
    assert response.status_code == 200
    assertContains(response, "KAT introduction")
    assertContains(response, "Setup scan")
    assertContains(response, "Let OpenKAT know what object to scan")
    assertContains(response, "Understanding objects")
    assertContains(response, "Skip onboarding")
    assertContains(response, "Add URL")


def test_onboarding_setup_scan_detail(
    rf, my_red_teamer, organization, mock_models_katalogus, mock_organization_view_octopoes, network
):
    mock_organization_view_octopoes().get.return_value = network

    request = setup_request(rf.get("step_setup_scan_ooi_add"), my_red_teamer)
    response = OnboardingSetupScanOOIAddView.as_view()(request, ooi_type="Network", organization_code=organization.code)

    assert response.status_code == 200
    assertContains(response, "KAT introduction")
    assertContains(response, "Setup scan")
    assertContains(response, "Creating an object")
    assertContains(response, "Dependencies")
    assertContains(response, "Create object")
    assertContains(response, "Skip onboarding")


def test_onboarding_set_clearance_level(
    rf, my_red_teamer, organization, mock_models_katalogus, mock_organization_view_octopoes, network
):
    mock_organization_view_octopoes().get.return_value = network

    request = setup_request(rf.get("step_set_clearance_level", {"ooi_id": "Network|internet"}), my_red_teamer)
    response = OnboardingSetClearanceLevelView.as_view()(request, organization_code=organization.code)

    assert response.status_code == 200
    assertContains(response, "KAT introduction")
    assertContains(response, "Set clearance level for")
    assertContains(response, "How to know required clearance level")
    assertContains(response, "Set clearance level")
    assertContains(response, "Skip onboarding")


def test_onboarding_select_plugins(
    rf, my_red_teamer, organization, mock_views_katalogus, mock_organization_view_octopoes, network
):
    mock_organization_view_octopoes().get.return_value = network

    request = setup_request(rf.get("step_setup_scan_select_plugins", {"ooi_id": "Network|internet"}), my_red_teamer)
    request.session["clearance_level"] = "2"
    response = OnboardingSetupScanSelectPluginsView.as_view()(request, organization_code=organization.code)

    assert response.status_code == 200
    assertContains(response, "Setup scan - Enable plugins")
    assertContains(response, "Plugins introduction")
    assertContains(response, "Boefjes")
    assertContains(response, "Normalizers")
    assertContains(response, "Bits")
    assertContains(response, "Suggested plugins")
    assertContains(response, "Skip onboarding")
    assertContains(response, "Enable and start scan")


def test_onboarding_ooi_detail_scan(
    rf, my_red_teamer, organization, mock_models_katalogus, mock_organization_view_octopoes, network
):
    mock_organization_view_octopoes().get.return_value = network

    request = setup_request(rf.get("step_setup_scan_ooi_detail", {"ooi_id": "Network|internet"}), my_red_teamer)
    request.session["clearance_level"] = "2"
    response = OnboardingSetupScanOOIDetailView.as_view()(request, organization_code=organization.code)

    assert response.status_code == 200
    assertContains(response, "KAT introduction")
    assertContains(response, "Setup scan")
    assertContains(response, "Creating an object")
    assertContains(response, "Network")
    assertContains(response, "Skip onboarding")
    assertContains(response, "Start scanning")


def test_onboarding_scanning_boefjes(
    rf, my_red_teamer, organization, mock_models_katalogus, mock_organization_view_octopoes, network
):
    mock_organization_view_octopoes().get.return_value = network

    request = setup_request(rf.get("step_report", {"ooi_id": "Network|internet"}), my_red_teamer)
    response = OnboardingReportView.as_view()(request, organization_code=organization.code)

    assert response.status_code == 200
    assertContains(response, "KAT introduction")
    assertContains(response, "Report")
    assertContains(response, "Boefjes are scanning")
    assertContains(response, "Open my DNS-report")
