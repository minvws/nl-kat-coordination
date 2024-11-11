from pytest_django.asserts import assertContains
from reports.views.report_overview import ReportHistoryView

from octopoes.models.exception import ObjectNotFoundException
from tests.conftest import setup_request


def test_report_overview_show_reports(rf, client_member, mock_organization_view_octopoes, report_list):
    """
    Will send the selected oois to the report type selection page.
    """

    mock_organization_view_octopoes().list_reports.return_value = report_list

    response = ReportHistoryView.as_view()(
        setup_request(rf.get("report_history"), client_member.user), organization_code=client_member.organization.code
    )

    assert response.status_code == 200

    assertContains(response, "Showing 3 of 3 reports")


def test_report_overview_rename_reports(rf, client_member, mock_organization_view_octopoes, report_list):
    """
    Renames a report
    """

    mock_organization_view_octopoes().list_reports.return_value = report_list
    report, subreports = report_list.items[0]
    mock_organization_view_octopoes().get.return_value = report

    request = setup_request(
        rf.post(
            "report_history",
            {
                "action": "rename",
                "report_name": "This is the new report name for testing",
                "report_reference": report.primary_key,
            },
        ),
        client_member.user,
    )

    response = ReportHistoryView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 200

    assert list(request._messages)[0].message == "Reports successfully renamed."

    assertContains(response, "This is the new report name for testing")


def test_report_overview_rename_non_existant_report(rf, client_member, mock_organization_view_octopoes, report_list):
    """
    Renames a report
    """

    mock_organization_view_octopoes().list_reports.return_value = report_list
    report, subreports = report_list.items[0]

    request = setup_request(
        rf.post(
            "report_history",
            {
                "action": "rename",
                "report_name": "This is the new report name for testing",
                "report_reference": report.primary_key,
            },
        ),
        client_member.user,
    )

    response = ReportHistoryView.as_view()(request, organization_code=client_member.organization.code)

    mock_organization_view_octopoes().get.side_effect = ObjectNotFoundException("Object not found.")

    assert response.status_code == 200

    assert (
        list(request._messages)[0].message == 'Report "This is the new report name for testing" could not be renamed.'
    )


def test_report_overview_delete_reports(rf, client_member, mock_organization_view_octopoes, report_list):
    """
    Deletes a report
    """

    mock_organization_view_octopoes().list_reports.return_value = report_list
    report, subreports = report_list.items[0]
    mock_organization_view_octopoes().get.return_value = report

    request = setup_request(
        rf.post("report_history", {"action": "delete", "report_reference": report.primary_key}), client_member.user
    )

    response = ReportHistoryView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 200

    assert list(request._messages)[0].message == "Deletion successful."


def test_report_overview_rerun_reports(rf, client_member, mock_organization_view_octopoes, report_list):
    """
    Rerun a report
    """

    mock_organization_view_octopoes().list_reports.return_value = report_list
    concatenated_report, subreports = report_list.items[
        2
    ]  # rerun a concat report to also check if subreports are created.
    mock_organization_view_octopoes().get.return_value = concatenated_report

    request = setup_request(
        rf.post("report_history", {"action": "rerun", "report_reference": concatenated_report.primary_key}),
        client_member.user,
    )

    response = ReportHistoryView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 200

    assert list(request._messages)[0].message == "Rerun successful"

    assertContains(response, concatenated_report.name)
