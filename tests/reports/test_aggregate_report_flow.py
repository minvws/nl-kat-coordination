import json

from pytest_django.asserts import assertContains

from files.models import File, ReportContent
from katalogus.models import Boefje
from octopoes.models.pagination import Paginated
from octopoes.models.types import OOIType
from reports.views.aggregate_report import (
    OOISelectionAggregateReportView,
    ReportTypesSelectionAggregateReportView,
    SaveAggregateReportView,
    SetupScanAggregateReportView,
)
from reports.views.base import ViewReportView
from tests.conftest import get_aggregate_report_data, setup_request


def test_select_all_oois_post_to_select_report_types(
    rf, client_member, valid_time, octopoes_api_connector, listed_hostnames
):
    """
    Will send the selected oois to the report type selection page.
    """

    octopoes_api_connector.list_objects.return_value = Paginated[OOIType](
        count=len(listed_hostnames), items=listed_hostnames
    )

    request = setup_request(
        rf.post(
            "aggregate_report_select_report_types",
            {"observed_at": valid_time.strftime("%Y-%m-%d"), "ooi": listed_hostnames},
        ),
        client_member.user,
    )

    response = ReportTypesSelectionAggregateReportView.as_view()(
        request, organization_code=client_member.organization.code
    )

    assert response.status_code == 200
    total_objects = str(len(listed_hostnames))
    assertContains(response, f"You have selected {total_objects} objects in the previous step.")


def test_select_some_oois_post_to_select_report_types(
    rf, client_member, valid_time, octopoes_api_connector, listed_hostnames
):
    """
    Will send the selected oois to the report type selection page.
    """

    octopoes_api_connector.list_objects.return_value = Paginated[OOIType](
        count=len(listed_hostnames), items=listed_hostnames
    )

    ooi_pks = [hostname.primary_key for hostname in listed_hostnames]
    selection = ooi_pks[0:2]

    request = setup_request(
        rf.post(
            "aggregate_report_select_report_types", {"observed_at": valid_time.strftime("%Y-%m-%d"), "ooi": selection}
        ),
        client_member.user,
    )

    response = ReportTypesSelectionAggregateReportView.as_view()(
        request, organization_code=client_member.organization.code
    )

    assert response.status_code == 200

    total_objects = str(len(selection))

    assertContains(response, f"You have selected {total_objects} objects in the previous step.")


def test_select_query_post_to_select_report_types(
    rf, client_member, valid_time, octopoes_api_connector, listed_hostnames
):
    """
    Will send the query to the report type selection page.
    """

    octopoes_api_connector.list_objects.return_value = Paginated[OOIType](
        count=len(listed_hostnames), items=listed_hostnames
    )

    request = setup_request(
        rf.post(
            "aggregate_report_select_report_types",
            {"observed_at": valid_time.strftime("%Y-%m-%d"), "object_selection": "query"},
        ),
        client_member.user,
    )

    response = ReportTypesSelectionAggregateReportView.as_view()(
        request, organization_code=client_member.organization.code
    )

    assert response.status_code == 200
    assert response.context_data["selected_oois"] == []

    assertContains(response, "You have selected a live set in the previous step.")
    assertContains(response, "this live set results in 0 objects.")


def test_change_ooi_selection_for_none_selection(
    rf, client_member, valid_time, octopoes_api_connector, listed_hostnames
):
    """
    Will send the selected oois to the report type selection page.
    """

    octopoes_api_connector.list_objects.return_value = Paginated[OOIType](
        count=len(listed_hostnames), items=listed_hostnames
    )

    request = setup_request(
        rf.post("aggregate_report_select_oois", {"observed_at": valid_time.strftime("%Y-%m-%d")}), client_member.user
    )

    response = OOISelectionAggregateReportView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 200
    assert response.context_data["selected_oois"] == []
    assert list(request._messages)[0].message == "Select at least one OOI to proceed."


def test_change_ooi_selection_with_ooi_selection(
    rf, client_member, valid_time, octopoes_api_connector, listed_hostnames
):
    """
    Will send the selected oois to the report type selection page.
    """

    octopoes_api_connector.list_objects.return_value = Paginated[OOIType](
        count=len(listed_hostnames), items=listed_hostnames
    )

    ooi_pks = [hostname.primary_key for hostname in listed_hostnames]
    selection = ooi_pks[0:2]

    request = setup_request(
        rf.post("aggregate_report_select_oois", {"observed_at": valid_time.strftime("%Y-%m-%d"), "ooi": selection}),
        client_member.user,
    )

    response = OOISelectionAggregateReportView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 200

    oois_fetched_from_post = response.context_data["selected_oois"]

    assert len(oois_fetched_from_post) == 2


def test_report_types_selection_nothing_selected(
    rf, client_member, valid_time, octopoes_api_connector, listed_hostnames
):
    """
    Will send the selected report types to the configuration page (set plugins).
    """

    octopoes_api_connector.list_objects.return_value = Paginated[OOIType](
        count=len(listed_hostnames), items=listed_hostnames
    )

    request = setup_request(
        rf.post("aggregate_report_setup_scan", {"observed_at": valid_time.strftime("%Y-%m-%d")}), client_member.user
    )

    response = SetupScanAggregateReportView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 307
    assert list(request._messages)[0].message == "Select at least one report type to proceed."


def test_report_types_selection(
    rf, client_member, valid_time, octopoes_api_connector, listed_hostnames, mocker, plugins, health, katalogus_client
):
    """
    Will send the selected report types to the configuration page (set plugins).
    """
    openkat_health_mocker = mocker.patch(
        "reports.report_types.aggregate_organisation_report.report.get_openkat_health"
    )()
    openkat_health_mocker.return_value = health

    octopoes_api_connector.list_objects.return_value = Paginated[OOIType](
        count=len(listed_hostnames), items=listed_hostnames
    )
    katalogus_client.enable_plugin(client_member.organization.code, Boefje.objects.get(plugin_id="dns-records"))
    katalogus_client.enable_plugin(client_member.organization.code, Boefje.objects.get(plugin_id="dns-zone"))
    katalogus_client.enable_plugin(client_member.organization.code, Boefje.objects.get(plugin_id="nmap"))
    katalogus_client.enable_plugin(client_member.organization.code, Boefje.objects.get(plugin_id="dns-sec"))
    katalogus_client.enable_plugin(client_member.organization.code, Boefje.objects.get(plugin_id="nmap-udp"))

    request = setup_request(
        rf.post(
            "aggregate_report_setup_scan",
            {"observed_at": valid_time.strftime("%Y-%m-%d"), "report_type": ["dns-report", "systems-report"]},
        ),
        client_member.user,
    )

    response = SetupScanAggregateReportView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 307  # if all plugins are enabled the view will auto redirect to generate report

    # Redirect to export setup
    assert (
        response.headers["Location"] == f"/en/{client_member.organization.code}/reports/aggregate-report/export-setup/?"
    )


def test_save_aggregate_report_view(
    rf, client_member, valid_time, octopoes_api_connector, listed_hostnames, health, mocker, plugins
):
    """
    Will send data through post to aggregate report and immediately creates a report (not scheduled).
    """
    openkat_health_mocker = mocker.patch(
        "reports.report_types.aggregate_organisation_report.report.get_openkat_health"
    )()
    openkat_health_mocker.return_value = health
    octopoes_api_connector.list_objects.return_value = Paginated[OOIType](
        count=len(listed_hostnames), items=listed_hostnames
    )

    request = setup_request(
        rf.post(
            "aggregate_report_save",
            {
                "observed_at": valid_time.strftime("%Y-%m-%d"),
                "ooi": listed_hostnames,
                "report_type": ["systems-report", "dns-report"],
                "start_date": "2024-01-01",
                "start_time": "10:10",
                "recurrence": "once",
                "parent_report_name_format": "${report_type} for ${oois_count} objects",
            },
        ),
        client_member.user,
    )

    response = SaveAggregateReportView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 302  # after post follows redirect, this to first create report ID
    assert "/reports/scheduled-reports/" in response.url


def test_save_aggregate_report_view_scheduled(
    rf, client_member, valid_time, octopoes_api_connector, listed_hostnames, health, mocker, plugins
):
    """
    Will send data through post to aggregate report and creates a scheduled aggregate report.
    """
    openkat_health_mocker = mocker.patch(
        "reports.report_types.aggregate_organisation_report.report.get_openkat_health"
    )()
    openkat_health_mocker.return_value = health
    octopoes_api_connector.list_objects.return_value = Paginated[OOIType](
        count=len(listed_hostnames), items=listed_hostnames
    )

    request = setup_request(
        rf.post(
            "aggregate_report_save",
            {
                "observed_at": valid_time.strftime("%Y-%m-%d"),
                "ooi": listed_hostnames,
                "report_type": ["systems-report", "vulnerability-report"],
                "start_date": "2024-01-01",
                "start_time": "10:10",
                "recurrence": "once",
                "parent_report_name_format": "${report_type} for ${oois_count} object(s)",
            },
        ),
        client_member.user,
    )

    response = SaveAggregateReportView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 302  # after post follows redirect, this to first create report ID
    assert response.url == f"/en/{client_member.organization.code}/reports/scheduled-reports/"


def test_json_download_aggregate_report(
    rf, client_member, get_aggregate_report_ooi, get_aggregate_report_from_bytes, octopoes_api_connector
):
    get_aggregate_report_ooi.data_raw_id = File.objects.create(file=ReportContent(get_aggregate_report_from_bytes)).id
    octopoes_api_connector.get_report.return_value = get_aggregate_report_ooi
    request = setup_request(
        rf.get("view_report_json", {"json": "true", "report_id": f"{get_aggregate_report_ooi.primary_key}"}),
        client_member.user,
    )

    json_response = ViewReportView.as_view()(request, organization_code=client_member.organization.code)

    assert json_response.status_code == 200

    json_response_data = json.dumps(json.loads(json_response.content))
    json_compare_data = json.dumps(get_aggregate_report_data())

    assert json_response_data == json_compare_data
