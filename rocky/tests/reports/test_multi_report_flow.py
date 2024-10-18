from pytest_django.asserts import assertContains
from reports.views.base import ViewReportView
from reports.views.multi_report import (
    MultiReportView,
    OOISelectionMultiReportView,
    ReportTypesSelectionMultiReportView,
    SetupScanMultiReportView,
)

from octopoes.models.pagination import Paginated
from octopoes.models.types import OOIType
from tests.conftest import setup_request


def test_multi_report_select_oois(
    rf, client_member, valid_time, mock_organization_view_octopoes, report_data_ooi_org_a, report_data_ooi_org_b
):
    """
    Will send the selected oois to the report type selection page.
    """

    oois = [report_data_ooi_org_a, report_data_ooi_org_b]
    oois_selection = [ooi.primary_key for ooi in oois]

    mock_organization_view_octopoes().list_objects.return_value = Paginated[OOIType](count=len(oois), items=oois)

    request = setup_request(
        rf.post(
            "multi_report_select_report_types", {"observed_at": valid_time.strftime("%Y-%m-%d"), "ooi": oois_selection}
        ),
        client_member.user,
    )

    response = ReportTypesSelectionMultiReportView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 200

    total_objects = str(len(oois_selection))

    assertContains(response, f"You have selected {total_objects} objects in previous step.")


def test_multi_report_change_ooi_selection(
    rf, client_member, valid_time, mock_organization_view_octopoes, report_data_ooi_org_a, report_data_ooi_org_b
):
    """
    Will send the selected oois back to the ooi selection page.
    """

    oois = [report_data_ooi_org_a, report_data_ooi_org_b]
    oois_selection = [ooi.primary_key for ooi in oois]

    mock_organization_view_octopoes().list_objects.return_value = Paginated[OOIType](count=len(oois), items=oois)

    request = setup_request(
        rf.post("multi_report_select_oois", {"observed_at": valid_time.strftime("%Y-%m-%d"), "ooi": oois_selection}),
        client_member.user,
    )

    response = OOISelectionMultiReportView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 200

    for response_ooi in response.context_data["selected_oois"]:
        assert response_ooi in oois_selection


def test_multi_report_report_types_selection(
    rf, client_member, valid_time, mock_organization_view_octopoes, report_data_ooi_org_a, report_data_ooi_org_b, mocker
):
    """
    Will send the selected report types to the configuration page (set plugins).
    """

    mocker.patch("reports.views.base.get_katalogus")()

    oois = [report_data_ooi_org_a, report_data_ooi_org_b]

    mock_organization_view_octopoes().list_objects.return_value = Paginated[OOIType](count=len(oois), items=oois)

    request = setup_request(
        rf.post(
            "multi_report_setup_scan",
            {"observed_at": valid_time.strftime("%Y-%m-%d"), "report_type": ["multi-organization-report"]},
        ),
        client_member.user,
    )

    response = SetupScanMultiReportView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 307  # if all plugins are enabled the view will auto redirect to generate report

    # Redirect to export setup
    assert response.headers["Location"] == "/en/test/reports/multi-report/export-setup/?"


def test_save_multi_report(
    rf,
    client_member,
    valid_time,
    mock_organization_view_octopoes,
    mocker,
    mock_bytes_client,
    report_data_ooi_org_a,
    report_data_ooi_org_b,
    multi_report_ooi,
):
    """
    Will send data through post to multi report.
    """

    mocker.patch("reports.views.base.get_katalogus")()
    oois = [report_data_ooi_org_a, report_data_ooi_org_b]
    oois_selection = [ooi.primary_key for ooi in oois]

    mock_bytes_client().upload_raw.return_value = multi_report_ooi.data_raw_id

    mock_organization_view_octopoes().list_objects.return_value = Paginated[OOIType](count=len(oois), items=oois)

    request = setup_request(
        rf.post(
            "multi_report_view",
            {
                "observed_at": valid_time.strftime("%Y-%m-%d"),
                "ooi": oois_selection,
                "report_type": ["multi-organization-report"],
                "old_report_name": ["Sector Report"],
                "report_name": ["Sector Report"],
            },
        ),
        client_member.user,
    )

    response = MultiReportView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 302  # after post follows redirect, this to first create report ID
    assert "report_id=Report" in response.url


def test_view_multi_report(
    rf,
    client_member,
    get_aggregate_report_ooi,
    get_aggregate_report_from_bytes,
    mock_organization_view_octopoes,
    mock_bytes_client,
    mock_katalogus_client,
):
    mock_organization_view_octopoes().get.return_value = get_aggregate_report_ooi
    mock_bytes_client().get_raw.return_value = get_aggregate_report_from_bytes
    mock_organization_view_octopoes().query.return_value = []

    request = setup_request(
        rf.get("view_report", {"report_id": f"{get_aggregate_report_ooi.primary_key}"}), client_member.user
    )

    response = ViewReportView.as_view()(request, organization_code=client_member.organization.code)
    assert response.status_code == 200
