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


def test_onboarding_introduction(rf, superuser_member, admin_member, redteam_member, client_member):
    response_superuser = OnboardingIntroductionView.as_view()(
        setup_request(rf.get("step_introduction"), superuser_member.user),
        organization_code=superuser_member.organization.code,
    )
    response_redteam = OnboardingIntroductionView.as_view()(
        setup_request(rf.get("step_introduction"), redteam_member.user),
        organization_code=redteam_member.organization.code,
    )

    assert response_redteam.status_code == 200
    assert response_superuser.status_code == 200
    assertContains(response_redteam, "Welcome to OpenKAT")
    assertContains(response_redteam, "Skip onboarding")
    assertContains(response_redteam, "Let's get started")

    with pytest.raises(PermissionDenied):
        OnboardingIntroductionView.as_view()(
            setup_request(rf.get("step_introduction"), admin_member.user),
            organization_code=admin_member.organization.code,
        )
    with pytest.raises(PermissionDenied):
        OnboardingIntroductionView.as_view()(
            setup_request(rf.get("step_introduction"), client_member.user),
            organization_code=client_member.organization.code,
        )


def test_onboarding_choose_report_info(rf, superuser_member, admin_member, redteam_member, client_member):
    response_superuser = OnboardingChooseReportInfoView.as_view()(
        setup_request(rf.get("step_choose_report_info"), superuser_member.user),
        organization_code=superuser_member.organization.code,
    )
    response_redteam = OnboardingChooseReportInfoView.as_view()(
        setup_request(rf.get("step_choose_report_info"), redteam_member.user),
        organization_code=redteam_member.organization.code,
    )

    assert response_redteam.status_code == 200
    assert response_superuser.status_code == 200

    assertContains(response_redteam, "KAT introduction")
    assertContains(response_redteam, "Reports")
    assertContains(response_redteam, "Data")
    assertContains(response_redteam, "Skip onboarding")
    assertContains(response_redteam, "Let's choose a report")

    with pytest.raises(PermissionDenied):
        OnboardingChooseReportInfoView.as_view()(
            setup_request(rf.get("step_choose_report_info"), admin_member.user),
            organization_code=admin_member.organization.code,
        )
    with pytest.raises(PermissionDenied):
        OnboardingChooseReportInfoView.as_view()(
            setup_request(rf.get("step_choose_report_info"), client_member.user),
            organization_code=client_member.organization.code,
        )


def test_onboarding_choose_report_type(rf, superuser_member, admin_member, redteam_member, client_member):
    response_superuser = OnboardingChooseReportTypeView.as_view()(
        setup_request(rf.get("step_choose_report_type"), superuser_member.user),
        organization_code=superuser_member.organization.code,
    )
    response_redteam = OnboardingChooseReportTypeView.as_view()(
        setup_request(rf.get("step_choose_report_type"), redteam_member.user),
        organization_code=redteam_member.organization.code,
    )

    assert response_redteam.status_code == 200
    assert response_superuser.status_code == 200
    assertContains(response_redteam, "KAT introduction")
    assertContains(response_redteam, "Choose a report - Type")
    assertContains(response_redteam, "Skip onboarding")
    assertContains(response_redteam, "DNS report")
    assertContains(response_redteam, "Pen test")
    assertContains(response_redteam, "Mail report")
    assertContains(response_redteam, "DigiD")

    with pytest.raises(PermissionDenied):
        OnboardingChooseReportTypeView.as_view()(
            setup_request(rf.get("step_choose_report_type"), admin_member.user),
            organization_code=admin_member.organization.code,
        )
    with pytest.raises(PermissionDenied):
        OnboardingChooseReportTypeView.as_view()(
            setup_request(rf.get("step_choose_report_type"), client_member.user),
            organization_code=client_member.organization.code,
        )


def test_onboarding_setup_scan(rf, superuser_member, admin_member, redteam_member, client_member):
    response_superuser = OnboardingSetupScanOOIInfoView.as_view()(
        setup_request(rf.get("step_setup_scan_ooi_info"), superuser_member.user),
        organization_code=superuser_member.organization.code,
    )
    response_redteam = OnboardingSetupScanOOIInfoView.as_view()(
        setup_request(rf.get("step_setup_scan_ooi_info"), redteam_member.user),
        organization_code=redteam_member.organization.code,
    )

    assert response_redteam.status_code == 200
    assert response_superuser.status_code == 200

    assertContains(response_redteam, "KAT introduction")
    assertContains(response_redteam, "Setup scan")
    assertContains(response_redteam, "Let OpenKAT know what object to scan")
    assertContains(response_redteam, "Understanding objects")
    assertContains(response_redteam, "Skip onboarding")
    assertContains(response_redteam, "Add URL")

    with pytest.raises(PermissionDenied):
        OnboardingSetupScanOOIInfoView.as_view()(
            setup_request(rf.get("step_setup_scan_ooi_info"), admin_member.user),
            organization_code=admin_member.organization.code,
        )
    with pytest.raises(PermissionDenied):
        OnboardingSetupScanOOIInfoView.as_view()(
            setup_request(rf.get("step_setup_scan_ooi_info"), client_member.user),
            organization_code=client_member.organization.code,
        )


def test_onboarding_setup_scan_detail(
    rf, superuser_member, admin_member, redteam_member, client_member, mock_organization_view_octopoes, network
):
    mock_organization_view_octopoes().get.return_value = network

    response_superuser = OnboardingSetupScanOOIAddView.as_view()(
        setup_request(rf.get("step_setup_scan_ooi_add"), superuser_member.user),
        ooi_type="Network",
        organization_code=superuser_member.organization.code,
    )
    response_redteam = OnboardingSetupScanOOIAddView.as_view()(
        setup_request(rf.get("step_setup_scan_ooi_add"), redteam_member.user),
        ooi_type="Network",
        organization_code=redteam_member.organization.code,
    )

    assert response_redteam.status_code == 200
    assert response_superuser.status_code == 200

    assertContains(response_redteam, "KAT introduction")
    assertContains(response_redteam, "Setup scan")
    assertContains(response_redteam, "Creating an object")
    assertContains(response_redteam, "Dependencies")
    assertContains(response_redteam, "Create object")
    assertContains(response_redteam, "Skip onboarding")

    with pytest.raises(PermissionDenied):
        OnboardingSetupScanOOIAddView.as_view()(
            setup_request(rf.get("step_setup_scan_ooi_add"), admin_member.user),
            ooi_type="Network",
            organization_code=admin_member.organization.code,
        )
    with pytest.raises(PermissionDenied):
        OnboardingSetupScanOOIAddView.as_view()(
            setup_request(rf.get("step_setup_scan_ooi_add"), client_member.user),
            ooi_type="Network",
            organization_code=client_member.organization.code,
        )


def test_onboarding_setup_scan_detail_create_ooi(
    rf, redteam_member, mock_organization_view_octopoes, network, mock_bytes_client
):
    mock_organization_view_octopoes().get.return_value = network

    request = setup_request(
        rf.post("step_setup_scan_ooi_add", {"network": "Network|internet", "raw": "http://example.org", "web_url": ""}),
        redteam_member.user,
    )
    response = OnboardingSetupScanOOIAddView.as_view()(
        request, ooi_type="URL", organization_code=redteam_member.organization.code
    )

    assert response.status_code == 302
    assert response.headers["Location"] == get_ooi_url(
        "step_set_clearance_level", "URL|internet|http://example.org", redteam_member.organization.code
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


def test_onboarding_select_plugins(
    rf,
    superuser_member,
    admin_member,
    redteam_member,
    client_member,
    mock_views_katalogus,
    mock_organization_view_octopoes,
    network,
):
    mock_organization_view_octopoes().get.return_value = network

    request_superuser = setup_request(
        rf.get("step_setup_scan_select_plugins", {"ooi_id": "Network|internet"}), superuser_member.user
    )
    request_redteam = setup_request(
        rf.get("step_setup_scan_select_plugins", {"ooi_id": "Network|internet"}), redteam_member.user
    )

    request_superuser.session["clearance_level"] = "2"
    request_redteam.session["clearance_level"] = "2"

    response_superuser = OnboardingSetupScanSelectPluginsView.as_view()(
        request_superuser, organization_code=superuser_member.organization.code
    )
    response_redteam = OnboardingSetupScanSelectPluginsView.as_view()(
        request_redteam, organization_code=redteam_member.organization.code
    )

    assert response_redteam.status_code == 200
    assert response_superuser.status_code == 200

    assertContains(response_redteam, "Setup scan - Enable plugins")
    assertContains(response_redteam, "Plugins introduction")
    assertContains(response_redteam, "Boefjes")
    assertContains(response_redteam, "Normalizers")
    assertContains(response_redteam, "Bits")
    assertContains(response_redteam, "Suggested plugins")
    assertContains(response_redteam, "Skip onboarding")
    assertContains(response_redteam, "Enable and start scan")

    with pytest.raises(PermissionDenied):
        OnboardingSetupScanSelectPluginsView.as_view()(
            setup_request(rf.get("step_setup_scan_select_plugins", {"ooi_id": "Network|internet"}), admin_member.user),
            organization_code=admin_member.organization.code,
        )
    with pytest.raises(PermissionDenied):
        OnboardingSetupScanSelectPluginsView.as_view()(
            setup_request(rf.get("step_setup_scan_select_plugins", {"ooi_id": "Network|internet"}), client_member.user),
            organization_code=client_member.organization.code,
        )


def test_onboarding_ooi_detail_scan(
    rf, superuser_member, admin_member, redteam_member, client_member, mock_organization_view_octopoes, network
):
    mock_organization_view_octopoes().get.return_value = network

    request_superuser = setup_request(
        rf.get("step_setup_scan_ooi_detail", {"ooi_id": "Network|internet"}), superuser_member.user
    )
    request_redteam = setup_request(
        rf.get("step_setup_scan_ooi_detail", {"ooi_id": "Network|internet"}), redteam_member.user
    )

    request_superuser.session["clearance_level"] = "2"
    request_redteam.session["clearance_level"] = "2"

    response_superuser = OnboardingSetupScanOOIDetailView.as_view()(
        request_superuser, organization_code=superuser_member.organization.code
    )
    response_redteam = OnboardingSetupScanOOIDetailView.as_view()(
        request_redteam, organization_code=redteam_member.organization.code
    )

    assert response_redteam.status_code == 200
    assert response_superuser.status_code == 200

    assertContains(response_redteam, "KAT introduction")
    assertContains(response_redteam, "Setup scan")
    assertContains(response_redteam, "Creating an object")
    assertContains(response_redteam, "Network")
    assertContains(response_redteam, "Skip onboarding")
    assertContains(response_redteam, "Start scanning")

    with pytest.raises(PermissionDenied):
        OnboardingSetupScanOOIDetailView.as_view()(
            setup_request(rf.get("step_setup_scan_ooi_detail", {"ooi_id": "Network|internet"}), admin_member.user),
            organization_code=admin_member.organization.code,
        )
    with pytest.raises(PermissionDenied):
        OnboardingSetupScanOOIDetailView.as_view()(
            setup_request(rf.get("step_setup_scan_ooi_detail", {"ooi_id": "Network|internet"}), client_member.user),
            organization_code=client_member.organization.code,
        )


def test_onboarding_scanning_boefjes(
    rf, superuser_member, admin_member, redteam_member, client_member, mock_organization_view_octopoes, network
):
    mock_organization_view_octopoes().get.return_value = network

    response_superuser = OnboardingReportView.as_view()(
        setup_request(rf.get("step_report", {"ooi_id": "Network|internet"}), superuser_member.user),
        organization_code=superuser_member.organization.code,
    )
    response_redteam = OnboardingReportView.as_view()(
        setup_request(rf.get("step_report", {"ooi_id": "Network|internet"}), redteam_member.user),
        organization_code=redteam_member.organization.code,
    )

    assert response_superuser.status_code == 200
    assert response_redteam.status_code == 200

    assertContains(response_redteam, "KAT introduction")
    assertContains(response_redteam, "Report")
    assertContains(response_redteam, "Boefjes are scanning")
    assertContains(response_redteam, "Open my DNS-report")

    with pytest.raises(PermissionDenied):
        OnboardingReportView.as_view()(
            setup_request(rf.get("step_report", {"ooi_id": "Network|internet"}), admin_member.user),
            organization_code=admin_member.organization.code,
        )
    with pytest.raises(PermissionDenied):
        OnboardingReportView.as_view()(
            setup_request(rf.get("step_report", {"ooi_id": "Network|internet"}), client_member.user),
            organization_code=client_member.organization.code,
        )
