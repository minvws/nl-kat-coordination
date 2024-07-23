from pytest_django.asserts import assertContains
from reports.views.aggregate_report import (
    OOISelectionAggregateReportView,
    ReportTypesSelectionAggregateReportView,
    SaveAggregateReportView,
    SetupScanAggregateReportView,
)

from octopoes.models.pagination import Paginated
from octopoes.models.types import OOIType
from tests.conftest import setup_request


def test_select_all_oois_post_to_select_report_types(
    rf,
    client_member,
    valid_time,
    mock_organization_view_octopoes,
    listed_hostnames,
):
    """
    Will send the selected oois to the report type selection page.
    """

    mock_organization_view_octopoes().list_objects.return_value = Paginated[OOIType](
        count=len(listed_hostnames), items=listed_hostnames
    )

    request = setup_request(
        rf.post(
            "aggregate_report_select_report_types",
            {
                "observed_at": valid_time.strftime("%Y-%m-%d"),
                "ooi": "all",
            },
        ),
        client_member.user,
    )

    response = ReportTypesSelectionAggregateReportView.as_view()(
        request, organization_code=client_member.organization.code
    )

    assert response.status_code == 200
    total_objects = str(len(listed_hostnames))
    assertContains(response, f"You have selected {total_objects} objects in previous step.")


def test_select_some_oois_post_to_select_report_types(
    rf,
    client_member,
    valid_time,
    mock_organization_view_octopoes,
    listed_hostnames,
):
    """
    Will send the selected oois to the report type selection page.
    """

    mock_organization_view_octopoes().list_objects.return_value = Paginated[OOIType](
        count=len(listed_hostnames), items=listed_hostnames
    )

    ooi_pks = [hostname.primary_key for hostname in listed_hostnames]
    selection = ooi_pks[0:2]

    request = setup_request(
        rf.post(
            "generate_report_select_report_types",
            {
                "observed_at": valid_time.strftime("%Y-%m-%d"),
                "ooi": selection,
            },
        ),
        client_member.user,
    )

    response = ReportTypesSelectionAggregateReportView.as_view()(
        request, organization_code=client_member.organization.code
    )

    assert response.status_code == 200

    total_objects = str(len(selection))

    assertContains(response, f"You have selected {total_objects} objects in previous step.")


def test_change_ooi_selection_for_none_selection(
    rf,
    client_member,
    valid_time,
    mock_organization_view_octopoes,
    listed_hostnames,
):
    """
    Will send the selected oois to the report type selection page.
    """

    mock_organization_view_octopoes().list_objects.return_value = Paginated[OOIType](
        count=len(listed_hostnames), items=listed_hostnames
    )

    request = setup_request(
        rf.post(
            "generate_report_select_oois",
            {
                "observed_at": valid_time.strftime("%Y-%m-%d"),
            },
        ),
        client_member.user,
    )

    response = OOISelectionAggregateReportView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 200
    assert response.context_data["selected_oois"] == []


def test_change_ooi_selection_with_ooi_selection(
    rf,
    client_member,
    valid_time,
    mock_organization_view_octopoes,
    listed_hostnames,
):
    """
    Will send the selected oois to the report type selection page.
    """

    mock_organization_view_octopoes().list_objects.return_value = Paginated[OOIType](
        count=len(listed_hostnames), items=listed_hostnames
    )

    ooi_pks = [hostname.primary_key for hostname in listed_hostnames]
    selection = ooi_pks[0:2]

    request = setup_request(
        rf.post(
            "generate_report_select_oois",
            {"observed_at": valid_time.strftime("%Y-%m-%d"), "ooi": selection},
        ),
        client_member.user,
    )

    response = OOISelectionAggregateReportView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 200

    oois_fetched_from_post = response.context_data["selected_oois"]

    assert len(oois_fetched_from_post) == 2


def test_report_types_selection_nothing_selected(
    rf,
    client_member,
    valid_time,
    mock_organization_view_octopoes,
    listed_hostnames,
):
    """
    Will send the selected report types to the configuration page (set plugins).
    """

    mock_organization_view_octopoes().list_objects.return_value = Paginated[OOIType](
        count=len(listed_hostnames), items=listed_hostnames
    )

    request = setup_request(
        rf.post(
            "aggregate_report_setup_scan",
            {"observed_at": valid_time.strftime("%Y-%m-%d")},
        ),
        client_member.user,
    )

    response = SetupScanAggregateReportView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 302
    assert list(request._messages)[0].message == "Select at least one report type to proceed."


def test_report_types_selection(
    rf,
    client_member,
    valid_time,
    mock_organization_view_octopoes,
    listed_hostnames,
):
    """
    Will send the selected report types to the configuration page (set plugins).
    """

    mock_organization_view_octopoes().list_objects.return_value = Paginated[OOIType](
        count=len(listed_hostnames), items=listed_hostnames
    )

    request = setup_request(
        rf.post(
            "aggregate_report_setup_scan",
            {"observed_at": valid_time.strftime("%Y-%m-%d"), "report_type": "dns-report"},
        ),
        client_member.user,
    )

    response = SetupScanAggregateReportView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 200


def test_save_generate_report_view(
    rf, client_member, valid_time, mock_organization_view_octopoes, listed_hostnames, rocky_health, mocker
):
    """
    Will send data through post to generate report.
    """

    mock_organization_view_octopoes().list_objects.return_value = Paginated[OOIType](
        count=len(listed_hostnames), items=listed_hostnames
    )

    rocky_health_mocker = mocker.patch("reports.report_types.aggregate_organisation_report.report.get_rocky_health")()
    rocky_health_mocker.return_value = rocky_health

    request = setup_request(
        rf.post(
            "aggregate_report_save",
            {
                "observed_at": valid_time.strftime("%Y-%m-%d"),
                "ooi": "all",
                "report_type": ["systems-report", "open-ports-report"],
            },
        ),
        client_member.user,
    )

    response = SaveAggregateReportView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 302  # after post follows redirect, this to first create report ID
    assert "report_id=Report" in response.url
