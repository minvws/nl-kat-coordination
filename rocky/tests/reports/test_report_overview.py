from uuid import uuid4

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


def test_report_overview_rename_reports(
    rf, client_member, mock_organization_view_octopoes, mock_bytes_client, report_list
):
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


def test_report_overview_rerun_reports(
    rf, client_member, mock_organization_view_octopoes, mock_bytes_client, get_report_input_data_from_bytes, report_list
):
    """
    Rerun a report
    """

    mock_organization_view_octopoes().list_reports.return_value = report_list

    concatenated_report, subreports = report_list.items[2]  # a concat report

    mock_organization_view_octopoes().get.return_value = concatenated_report
    mock_bytes_client().get_raw.return_value = get_report_input_data_from_bytes
    mock_bytes_client().upload_raw.return_value = str(uuid4())
    mock_organization_view_octopoes().query.return_value = subreports

    request = setup_request(
        rf.post("report_history", {"action": "rerun", "report_reference": concatenated_report.primary_key}),
        client_member.user,
    )

    response = ReportHistoryView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 200

    assert list(request._messages)[0].message == "Rerun successful"

    assertContains(response, concatenated_report.name)


def test_aggregate_report_has_sub_reports(
    rf, client_member, mock_organization_view_octopoes, mock_bytes_client, aggregate_report_with_sub_reports
):
    mock_organization_view_octopoes().list_reports.return_value = aggregate_report_with_sub_reports

    aggregate_report, subreports = aggregate_report_with_sub_reports.items[0]

    response = ReportHistoryView.as_view()(
        setup_request(rf.get("report_history"), client_member.user), organization_code=client_member.organization.code
    )

    assert response.status_code == 200

    assertContains(response, "Nov. 21, 2024")
    assertContains(response, "Nov. 21, 2024, 10:07 a.m.")

    assertContains(response, "expando-button icon ti-chevron-down")

    assertContains(
        response, f"This report consist of {len(subreports)} subreports with the following report types and objects."
    )

    assertContains(response, f"Subreports (5/{len(subreports)})", html=True)

    assertContains(response, aggregate_report.name)

    for subreport in subreports:
        assertContains(response, subreport.name)

    assertContains(response, "View all subreports")
