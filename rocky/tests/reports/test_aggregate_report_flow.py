from pytest_django.asserts import assertContains
from reports.views.aggregate_report import OOISelectionAggregateReportView, ReportTypesSelectionAggregateReportView

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
