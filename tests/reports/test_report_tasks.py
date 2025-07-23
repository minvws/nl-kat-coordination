from pytest_django.asserts import assertContains

from openkat.views.tasks import ReportsTaskListView
from tests.conftest import setup_request


def test_report_task_list(rf, client_member, mock_scheduler, reports_task_list_db):
    recipe_ids = [report_task.data["report_recipe_id"] for report_task in reports_task_list_db]

    response = ReportsTaskListView.as_view()(
        setup_request(rf.get("reports_task_list"), client_member.user),
        organization_code=client_member.organization.code,
    )

    assert response.status_code == 200

    assertContains(response, "List of tasks for reports")
    assertContains(response, '<td><i class="icon failed"></i>Failed</td>', html=True)
    assertContains(response, '<td><i class="icon completed"></i>Completed</td>', html=True)
    assertContains(response, recipe_ids[0])
    assertContains(response, recipe_ids[1])
