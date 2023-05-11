from unittest.mock import call

from pytest_django.asserts import assertContains
from requests import HTTPError

from rocky.views.tasks import BoefjesTaskListView
from tests.conftest import setup_request


def test_boefjes_tasks(rf, client_member, mocker, lazy_task_list_empty):
    mock_scheduler_client = mocker.patch("rocky.views.tasks.client")
    mock_scheduler_client.get_lazy_task_list.return_value = lazy_task_list_empty

    request = setup_request(rf.get("boefjes_task_list"), client_member.user)
    response = BoefjesTaskListView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 200

    mock_scheduler_client.get_lazy_task_list.assert_has_calls(
        [
            call(
                scheduler_id="boefje-test",
                task_type="boefje",
                status=None,
                min_created_at=None,
                max_created_at=None,
            )
        ]
    )


def test_tasks_view_simple(rf, client_member, mock_scheduler_client_task_list):
    request = setup_request(rf.get("boefjes_task_list"), client_member.user)
    response = BoefjesTaskListView.as_view()(request, organization_code=client_member.organization.code)

    assertContains(response, "2e757dd3")
    assertContains(response, "Hostname|internet|example.com")
    assertContains(response, "Completed")


def test_tasks_view_error(rf, client_member, mocker, lazy_task_list_with_boefje):
    mock_scheduler_client = mocker.patch("rocky.views.tasks.client")
    mock_scheduler_client.get_lazy_task_list.return_value = lazy_task_list_with_boefje
    mock_scheduler_client.get_lazy_task_list.side_effect = HTTPError

    request = setup_request(rf.get("boefjes_task_list"), client_member.user)
    response = BoefjesTaskListView.as_view()(request, organization_code=client_member.organization.code)

    assertContains(response, "error")
    assertContains(response, "Fetching tasks failed")
