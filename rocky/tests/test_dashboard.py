from crisis_room.views import CrisisRoom, DashboardService
from pytest_django.asserts import assertContains

from tests.conftest import setup_request


def test_crisis_room_findings_dashboard(rf, mocker, client_member, findings_dashboard_mock_data):
    """Test if the view is visible and if data is shown in the tables."""
    dashboard_service = mocker.patch("crisis_room.views.DashboardService")()
    dashboard_service.collect_findings_dashboard.return_value = findings_dashboard_mock_data
    summary = dashboard_service.get_organizations_findings_summary.side_effect = (
        DashboardService().get_organizations_findings_summary
    )
    summary(findings_dashboard_mock_data)

    request = setup_request(rf.get("crisis_room"), client_member.user)
    response = CrisisRoom.as_view()(request)

    assert response.status_code == 200
    # View should show the 'Findings overview' for all organizations
    assertContains(response, "<h2>Findings overview</h2>", html=True)
    assertContains(response, '<caption class="visually-hidden">Total per severity overview</caption>', html=True)
    assertContains(
        response,
        '<tr><td><span class="critical">Critical</span></td><td class="number">1</td><td class="number">3</td></tr>',
        html=True,
    )
    assertContains(response, '<tr><td>Total</td><td class="number">16</td><td class="number">24</td></tr>', html=True)

    # View should also show the 'Findings for all orgniazations' table for all organizations
    assertContains(response, "<h2>Findings per organization</h2>", html=True)
    assertContains(response, '<caption class="visually-hidden">Findings per organization overview</caption>', html=True)

    assertContains(response, '<td><a href="/en/test/">Test Organization</a></td>', html=True)
    assertContains(response, "<h5>Findings overview</h5>", html=True)
    assertContains(response, '<td>Total</td><td class="number">4</td><td class="number">7</td>', html=True)

    assertContains(response, '<td><a href="/en/org_b/">OrganizationB</a></td>', html=True)
    assertContains(response, '<td>Total</td><td class="number">12</td><td class="number">17</td>', html=True)
    assertContains(
        response, "<p>No critical and high findings have been identified for this organization.</p>", html=True
    )


def test_get_organizations_findings_summary(findings_dashboard_mock_data):
    """Test if summary has counted the results of both reports correctly."""
    dashboard_service = DashboardService()
    summary_results = dashboard_service.get_organizations_findings_summary(findings_dashboard_mock_data)

    assert summary_results["total_by_severity_per_finding_type"] == {
        "critical": 1,
        "high": 2,
        "medium": 7,
        "low": 3,
        "recommendation": 1,
        "pending": 1,
        "unknown": 1,
    }
    assert summary_results["total_by_severity"] == {
        "critical": 3,
        "high": 3,
        "medium": 9,
        "low": 6,
        "recommendation": 1,
        "pending": 1,
        "unknown": 1,
    }
    assert summary_results["total_finding_types"] == 16
    assert summary_results["total_occurrences"] == 24


def test_get_organizations_findings_summary_no_input():
    """Test if summary returns an empty dict if there is not input."""
    dashboard_service = DashboardService()
    summary_results = dashboard_service.get_organizations_findings_summary({})

    assert summary_results == {}


def test_get_organizations_findings(findings_report_bytes_data):
    """Test if the highest risk level is collected, only critical and high finding types are returned."""
    dashboard_service = DashboardService()
    report_data = list(findings_report_bytes_data.values())[0]

    report_data["findings"]["finding_types"] = [
        {"finding_type": {"risk_severity": "critical"}, "occurrences": {}},
        {"finding_type": {"risk_severity": "high"}, "occurrences": {}},
        {"finding_type": {"risk_severity": "low"}, "occurrences": {}},
    ]
    findings = dashboard_service.get_organizations_findings(report_data)

    assert len(findings["findings"]["finding_types"]) == 2
    assert findings["highest_risk_level"] == "critical"
    assert findings["findings"]["finding_types"][0]["finding_type"]["risk_severity"] == "critical"
    assert findings["findings"]["finding_types"][1]["finding_type"]["risk_severity"] == "high"


def test_get_organizations_findings_no_finding_types(findings_report_bytes_data):
    """
    When there are no finding types, the result should contain the report data and
    highest_risk_level should be an empty string.
    """
    dashboard_service = DashboardService()
    report_data = list(findings_report_bytes_data.values())[0]
    findings = dashboard_service.get_organizations_findings(report_data)

    assert findings == report_data | {"highest_risk_level": ""}


def test_get_organizations_findings_no_input():
    """When there is no input, the result should only contain an empty highest_risk_level"""
    dashboard_service = DashboardService()
    findings = dashboard_service.get_organizations_findings({})

    assert findings == {"highest_risk_level": ""}


def test_collect_findings_dashboard(
    mocker, dashboard_data, findings_reports, findings_report_bytes_data, findings_dashboard_mock_data
):
    """
    Test if the right dashboard is filtered and if the method returns the right dict format.
    Only the most recent report should be visible in the dict.
    """

    octopoes_client = mocker.patch("crisis_room.views.OctopoesAPIConnector")
    octopoes_client().bulk_list_reports.return_value = findings_reports

    bytes_client = mocker.patch("crisis_room.views.get_bytes_client")

    bytes_client().get_raws_all.return_value = findings_report_bytes_data

    organizations = [data.dashboard.organization for data in dashboard_data]

    dashboard_service = DashboardService()
    findings_dashboard = dashboard_service.collect_findings_dashboard(organizations)

    assert findings_dashboard[0]["report"] == list(findings_reports.values())[0]
    assert findings_dashboard[0]["report_data"] == dashboard_service.get_organizations_findings(
        list(findings_report_bytes_data.values())[0]
    )
