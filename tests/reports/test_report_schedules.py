from octopoes.models.exception import ObjectNotFoundException
from reports.views.report_overview import ScheduledReportsView
from tests.conftest import setup_request


def test_delete_schedule(
    rf, redteam_member, octopoes_api_connector, mock_scheduler, scheduled_report_recipe, report_schedule
):
    octopoes_api_connector.get.return_value = scheduled_report_recipe

    schedule_id = report_schedule.id
    recipe_id = "ReportRecipe|" + report_schedule.data["report_recipe_id"]

    request = setup_request(
        rf.post("scheduled_reports", {"report_recipe": recipe_id, "schedule_id": schedule_id}), redteam_member.user
    )

    response = ScheduledReportsView.as_view()(request, organization_code=redteam_member.organization.code)

    assert response.status_code == 302
    assert list(request._messages)[0].message == f"Recipe '{recipe_id}' deleted successfully"


def test_delete_schedule_no_recipe(
    rf, redteam_member, octopoes_api_connector, mock_scheduler, scheduled_report_recipe, report_schedule
):
    octopoes_api_connector.get.return_value = scheduled_report_recipe
    schedule_id = report_schedule.id

    request = setup_request(
        rf.post("scheduled_reports", {"report_recipe": "", "schedule_id": schedule_id}), redteam_member.user
    )

    response = ScheduledReportsView.as_view()(request, organization_code=redteam_member.organization.code)

    assert response.status_code == 302
    assert list(request._messages)[0].message == "No schedule or recipe selected"


def test_delete_schedule_object_not_found(
    rf, redteam_member, octopoes_api_connector, mock_scheduler, scheduled_report_recipe, report_schedule
):
    octopoes_api_connector.get.return_value = scheduled_report_recipe
    octopoes_api_connector.delete.side_effect = ObjectNotFoundException("Not found")

    request = setup_request(
        rf.post("scheduled_reports", {"report_recipe": "ReportRecipe|recipeNone", "schedule_id": report_schedule.id}),
        redteam_member.user,
    )

    response = ScheduledReportsView.as_view()(request, organization_code=redteam_member.organization.code)

    assert response.status_code == 302
    assert list(request._messages)[0].message == "Recipe not found."


def test_delete_schedule_schedule_not_found(
    rf, redteam_member, octopoes_api_connector, mock_scheduler, scheduled_report_recipe, report_schedule
):
    octopoes_api_connector.get.return_value = scheduled_report_recipe

    request = setup_request(
        rf.post("scheduled_reports", {"report_recipe": "ReportRecipe|recipeNone", "schedule_id": 0}),
        redteam_member.user,
    )

    response = ScheduledReportsView.as_view()(request, organization_code=redteam_member.organization.code)

    assert response.status_code == 302
    assert list(request._messages)[0].message == "Schedule not found."
