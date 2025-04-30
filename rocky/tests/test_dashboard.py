from crisis_room.views import CrisisRoomView, DashboardService
from pytest_django.asserts import assertContains

from tests.conftest import setup_request


def test_expected_findings_results_dashboard(rf, mocker, client_member, expected_findings_results):
    """Test if the view is visible and if data is shown in the tables."""

    dashboard_service = mocker.patch("crisis_room.views.DashboardService")()
    dashboard_service.get_dashboard_items.return_value = expected_findings_results

    summary = dashboard_service.get_organizations_findings_summary.side_effect = (
        DashboardService().get_organizations_findings_summary
    )
    summary_data = summary(expected_findings_results)

    total_finding_types = summary_data["total_finding_types"]
    total_occurrences = summary_data["total_occurrences"]

    org_code_a, org_name_a = (
        expected_findings_results[0].item.dashboard.organization.code,
        expected_findings_results[0].item.dashboard.organization.name,
    )
    org_code_b, org_name_b = (
        expected_findings_results[1].item.dashboard.organization.code,
        expected_findings_results[1].item.dashboard.organization.name,
    )

    request = setup_request(rf.get("crisis_room"), client_member.user)
    response = CrisisRoomView.as_view()(request)

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

    assertContains(response, f'<td><a href="/en/crisis-room/{org_code_a}/">{org_name_a}</a></td>', html=True)
    assertContains(response, "<h5>Findings overview</h5>", html=True)
    assertContains(response, '<td>Total</td><td class="number">4</td><td class="number">7</td>', html=True)

    assertContains(response, f'<td><a href="/en/crisis-room/{org_code_b}/">{org_name_b}</a></td>', html=True)

    assertContains(
        response,
        f'<td>Total</td><td class="number">{total_finding_types}</td><td class="number">{total_occurrences}</td>',
        html=True,
    )
    assertContains(
        response, "<p>No critical and high findings have been identified for this organization.</p>", html=True
    )


def test_get_organizations_findings_summary(expected_findings_results):
    """Test if summary has counted the results of both reports correctly."""
    dashboard_service = DashboardService()
    summary_results = dashboard_service.get_organizations_findings_summary(expected_findings_results)

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


def test_get_organizations_findings(findings_reports_data):
    """Test if the highest risk level is collected, only critical and high finding types are returned."""
    dashboard_service = DashboardService()
    report_data = list(findings_reports_data.values())[0]

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


def test_get_organizations_findings_no_finding_types(findings_reports_data):
    """
    When there are no finding types, the result should contain the report data and
    highest_risk_level should be an empty string.
    """
    dashboard_service = DashboardService()
    report_data = list(findings_reports_data.values())[0]
    findings = dashboard_service.get_organizations_findings(report_data)

    assert findings == report_data | {"highest_risk_level": ""}


def test_get_organizations_findings_no_input():
    """When there is no input, the result should only contain an empty highest_risk_level"""
    dashboard_service = DashboardService()
    findings = dashboard_service.get_organizations_findings({})

    assert findings == {"highest_risk_level": ""}


def test_collect_findings_dashboard(findings_results, expected_findings_results):
    """
    Test if the right dashboard is filtered and if the method returns the right dict format.
    Only the most recent report should be visible in the dict.
    """

    assert len(findings_results) == len(expected_findings_results)

    for index in range(len(findings_results)):
        assert findings_results[index].item == expected_findings_results[index].item
        assert findings_results[index].data["report"] == expected_findings_results[index].data["report"]
        assert findings_results[index].data["report_data"] == expected_findings_results[index].data["report_data"]
