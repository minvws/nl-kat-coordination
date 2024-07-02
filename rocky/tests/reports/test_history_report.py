from django.urls import resolve, reverse
from pytest_django.asserts import assertContains, assertNotContains
from reports.views.report_overview import ReportHistoryView, SubreportView

from octopoes.models.ooi.reports import Report
from octopoes.models.pagination import Paginated
from tests.conftest import setup_request


def test_report_history_one_subreports_one_input_objects(
    rf, client_member, mock_organization_view_octopoes, mocker, report_list_one_subreport
):
    """
    Test with one subreports and one input objects. Should contain:
        - Url of input item
        - No chevron down button
        - No "View all subreports" button
    """
    mocker.patch("reports.views.base.get_katalogus")
    kwargs = {"organization_code": client_member.organization.code}
    url = reverse("report_history", kwargs=kwargs)

    request = rf.get(
        url,
    )
    request.resolver_match = resolve(url)

    setup_request(request, client_member.user)

    mock_organization_view_octopoes().list_reports.return_value = Paginated[tuple[Report, list[Report | None]]](
        count=len(report_list_one_subreport), items=report_list_one_subreport
    )

    response = ReportHistoryView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 200

    # Check table rows
    subreport = report_list_one_subreport[0][0]
    assertContains(response, subreport)
    assertContains(
        response,
        '<a href="/en/test/objects/detail/?ooi_id=Hostname%7Cinternet%7Cexample.com">example.com</a>',
        html=True,
    )
    assertNotContains(response, "Close children report object details")

    # Check subreports, show only 5
    assertNotContains(response, "This report consist of ")

    # Check if all report types are shown
    assertContains(response, "RPKI Report")


def test_report_history_less_than_five_subreports_two_input_objects(
    rf, client_member, mock_organization_view_octopoes, mocker, report_list_two_subreports
):
    """
    Test with less than 5 subreports and two input objects. Should contain:
    - Number of input objects
    - Chevron down button
    - Only 5 subreports should be shown
    - No "View all subreports" button
    """

    mocker.patch("reports.views.base.get_katalogus")
    kwargs = {"organization_code": client_member.organization.code}
    url = reverse("report_history", kwargs=kwargs)

    request = rf.get(
        url,
    )
    request.resolver_match = resolve(url)

    setup_request(request, client_member.user)

    mock_organization_view_octopoes().list_reports.return_value = Paginated[tuple[Report, list[Report | None]]](
        count=len(report_list_two_subreports), items=report_list_two_subreports
    )

    response = ReportHistoryView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 200

    # Check table rows
    parent_report = report_list_two_subreports[0][0]
    assertContains(response, parent_report)
    assertContains(response, "<td>2</td>", html=True)
    assertContains(response, "Close children report object details")

    # Check subreports, show only 5
    total_subreports = str(len(report_list_two_subreports[0][1]))
    child_report_1 = report_list_two_subreports[0][1][0]
    child_report_2 = report_list_two_subreports[0][1][1]
    assertContains(response, f"{total_subreports}/{total_subreports}")
    assertContains(
        response, f"This report consist of {total_subreports} subreports with the following report types and objects."
    )
    assertNotContains(
        response,
        (
            '<a href="/en/test/reports/report-history/subreports?'
            f'report_id={parent_report}" class="button">View all subreports</a>'
        ),
        html=True,
    )
    assertContains(response, child_report_1)
    assertContains(response, child_report_2)

    # Check if all report types are shown
    assertContains(response, "Web System Report")


def test_report_history_more_than_five_subreports_one_input_object(
    rf, client_member, mock_organization_view_octopoes, mocker, report_list_six_subreports
):
    """
    Test with more than 5 subreports and one input object. Should contain:
    - Url of input item
    - Chevron down button
    - Only 5 subreports should be shown
    - "View all subreports" button

    """
    mocker.patch("reports.views.base.get_katalogus")
    kwargs = {"organization_code": client_member.organization.code}
    url = reverse("report_history", kwargs=kwargs)

    request = rf.get(
        url,
    )
    request.resolver_match = resolve(url)

    setup_request(request, client_member.user)

    mock_organization_view_octopoes().list_reports.return_value = Paginated[tuple[Report, list[Report | None]]](
        count=len(report_list_six_subreports), items=report_list_six_subreports
    )

    response = ReportHistoryView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 200

    # Check table rows
    parent_report = report_list_six_subreports[0][0]
    assertContains(response, parent_report)
    assertContains(
        response,
        '<a href="/en/test/objects/detail/?ooi_id=Hostname%7Cinternet%7Cexample.com">example.com</a>',
        html=True,
    )
    assertContains(response, "Close children report object details")

    # Check subreports, show only 5
    total_subreports = str(len(report_list_six_subreports[0][1]))
    child_report_1 = report_list_six_subreports[0][1][0]
    child_report_2 = report_list_six_subreports[0][1][1]
    child_report_3 = report_list_six_subreports[0][1][2]
    child_report_4 = report_list_six_subreports[0][1][3]
    child_report_5 = report_list_six_subreports[0][1][4]
    child_report_6 = report_list_six_subreports[0][1][5]
    assertContains(response, f"5/{total_subreports}")
    assertContains(
        response, f"This report consist of {total_subreports} subreports with the following report types and objects."
    )
    assertContains(
        response,
        (
            '<a href="/en/test/reports/report-history/subreports?'
            f'report_id={parent_report}" class="button">View all subreports</a>'
        ),
        html=True,
    )
    assertContains(response, child_report_1)
    assertContains(response, child_report_2)
    assertContains(response, child_report_3)
    assertContains(response, child_report_4)
    assertContains(response, child_report_5)
    assertNotContains(response, child_report_6)

    # Check if all report types are shown
    assertContains(response, "RPKI Report")
    assertContains(response, "Safe Connections Report")
    assertContains(response, "System Report")
    assertContains(response, "Mail Report")
    assertContains(response, "IPv6 Report")
    assertContains(response, "Web System Report")


# Test if the subreports that belong to one parent are collected well enough
def test_report_history_subreports_table(
    rf, client_member, mock_organization_view_octopoes, mocker, report_list_six_subreports, get_subreports
):
    mocker.patch("reports.views.base.get_katalogus")
    kwargs = {"organization_code": client_member.organization.code}
    url = reverse("subreports", kwargs=kwargs)
    parent_report = report_list_six_subreports[0][0]

    request = rf.get(url, {"report_id": parent_report.primary_key})
    request.resolver_match = resolve(url)

    setup_request(request, client_member.user)

    mock_organization_view_octopoes().query_many.return_value = get_subreports

    response = SubreportView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 200

    # Check header
    assertContains(
        response,
        f'<a href="/en/test/reports/view?report_id={parent_report}" title="Shows report details">{parent_report}</a>',
        html=True,
    )
    assertContains(response, "<h1>Subreports</h1>", html=True)
    assertContains(
        response,
        (
            '<a class="button ghost" href="/en/test/reports/report-history/">'
            '<span class="icon ti-chevron-left"></span>Back to Reports History</a>'
        ),
        html=True,
    )

    # Check table rows
    assertContains(
        response,
        '<a href="/en/test/objects/detail/?ooi_id=Hostname%7Cinternet%7Cexample.com">example.com</a>',
        html=True,
    )

    # Check subreports, show only 5
    total_subreports = str(len(report_list_six_subreports[0][1]))
    child_report_1 = report_list_six_subreports[0][1][0]
    child_report_2 = report_list_six_subreports[0][1][1]
    child_report_3 = report_list_six_subreports[0][1][2]
    child_report_4 = report_list_six_subreports[0][1][3]
    child_report_5 = report_list_six_subreports[0][1][4]
    child_report_6 = report_list_six_subreports[0][1][5]
    assertContains(response, f"Showing {total_subreports} of {total_subreports} subreports")
    assertContains(response, child_report_1)
    assertContains(response, child_report_2)
    assertContains(response, child_report_3)
    assertContains(response, child_report_4)
    assertContains(response, child_report_5)
    assertContains(response, child_report_6)

    # Check if all report types are shown
    assertContains(response, "RPKI Report")
    assertContains(response, "Safe Connections Report")
    assertContains(response, "System Report")
    assertContains(response, "Mail Report")
    assertContains(response, "IPv6 Report")
    assertContains(response, "Web System Report")


def test_report_history_report_type_summary(
    rf, client_member, mock_organization_view_octopoes, mocker, reports_more_input_oois
):
    mocker.patch("reports.views.base.get_katalogus")
    request = setup_request(rf.get("report_history"), client_member.user)

    mock_organization_view_octopoes().list_reports.return_value = Paginated[tuple[Report, list[Report | None]]](
        count=len(reports_more_input_oois), items=reports_more_input_oois
    )

    response = ReportHistoryView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 200

    assertContains(response, "RPKI Report")
    assertContains(response, "Safe Connections Report")
    assertContains(response, "This report consist of 4 subreports with the following report types and objects.")
    assertContains(response, "<td>4</td>", html=True)
