from reports.views.report_overview import ScheduledReportsView

from octopoes.models.exception import ObjectNotFoundException
from rocky.scheduler import SchedulerError
from tests.conftest import setup_request


def test_delete_schedule(
    rf, client_member, mock_organization_view_octopoes, mock_scheduler, scheduled_report_recipe, scheduled_reports_list
):
    mock_scheduler.get_scheduled_reports.return_value = scheduled_reports_list
    mock_organization_view_octopoes().get.return_value = scheduled_report_recipe

    schedule_id = scheduled_reports_list[0].id
    recipe_id = "ReportRecipe|" + scheduled_reports_list[0].data["report_recipe_id"]

    request = setup_request(
        rf.post("scheduled_reports", {"report_recipe": recipe_id, "schedule_id": schedule_id}), client_member.user
    )

    response = ScheduledReportsView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 302
    assert list(request._messages)[0].message == f"Recipe '{recipe_id}' deleted successfully"


def test_delete_schedule_no_recipe(
    rf, client_member, mock_organization_view_octopoes, mock_scheduler, scheduled_report_recipe, scheduled_reports_list
):
    mock_scheduler.get_scheduled_reports.return_value = scheduled_reports_list
    mock_organization_view_octopoes().get.return_value = scheduled_report_recipe

    schedule_id = scheduled_reports_list[0].id

    request = setup_request(
        rf.post("scheduled_reports", {"report_recipe": "", "schedule_id": schedule_id}), client_member.user
    )

    response = ScheduledReportsView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 302
    assert list(request._messages)[0].message == "No schedule or recipe selected"


def test_delete_schedule_object_not_found(
    rf, client_member, mock_organization_view_octopoes, mock_scheduler, scheduled_report_recipe, scheduled_reports_list
):
    mock_scheduler.get_scheduled_reports.side_effect = scheduled_reports_list
    mock_organization_view_octopoes().get.return_value = scheduled_report_recipe
    mock_organization_view_octopoes().delete.side_effect = ObjectNotFoundException("Not found")

    request = setup_request(
        rf.post("scheduled_reports", {"report_recipe": "recipeNone", "schedule_id": "ScheduleNone"}), client_member.user
    )

    response = ScheduledReportsView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 302
    assert list(request._messages)[0].message == "Recipe not found."


def test_delete_schedule_schedule_not_found(
    rf, client_member, mock_organization_view_octopoes, mock_scheduler, scheduled_report_recipe, scheduled_reports_list
):
    mock_scheduler.get_scheduled_reports.side_effect = scheduled_reports_list
    mock_organization_view_octopoes().get.return_value = scheduled_report_recipe
    mock_scheduler.delete_schedule.side_effect = SchedulerError

    request = setup_request(
        rf.post("scheduled_reports", {"report_recipe": "recipeNone", "schedule_id": "ScheduleNone"}), client_member.user
    )

    response = ScheduledReportsView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 302
    assert (
        list(request._messages)[0].message
        == "The Scheduler has an unexpected error. Check the Scheduler logs for further details."
    )
