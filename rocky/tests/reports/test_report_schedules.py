from reports.views.report_overview import ScheduledReportsDeleteView

from tests.conftest import setup_request


def test_delete_schedule(
    rf, client_member, mock_organization_view_octopoes, mock_scheduler, scheduled_report_recipe, scheduled_reports_list
):
    mock_scheduler.get_scheduled_reports.return_value = scheduled_reports_list
    mock_organization_view_octopoes().get.return_value = scheduled_report_recipe

    schedule_id = scheduled_reports_list[0]["id"]
    recipe_id = "ReportRecipe|" + scheduled_reports_list[0]["data"]["report_recipe_id"]

    request = setup_request(
        rf.post("delete_scheduled_reports", {"report_recipe": recipe_id, "schedule_id": schedule_id}),
        client_member.user,
    )

    response = ScheduledReportsDeleteView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 302
    assert list(request._messages)[0].message == f"Recipe '{recipe_id}' deleted successfully"


def test_delete_schedule_no_recipe(
    rf, client_member, mock_organization_view_octopoes, mock_scheduler, scheduled_report_recipe, scheduled_reports_list
):
    mock_scheduler.get_scheduled_reports.return_value = scheduled_reports_list
    mock_organization_view_octopoes().get.return_value = scheduled_report_recipe

    schedule_id = scheduled_reports_list[0]["id"]

    request = setup_request(
        rf.post("delete_scheduled_reports", {"report_recipe": "", "schedule_id": schedule_id}), client_member.user
    )

    response = ScheduledReportsDeleteView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 302
    assert list(request._messages)[0].message == "No schedule or recipe selected"
