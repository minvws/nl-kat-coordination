from http import HTTPStatus
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
                input_ooi=None,
            )
        ]
    )


def test_tasks_view_simple(rf, client_member, mocker, lazy_task_list_with_boefje):
    mock_scheduler_client = mocker.patch("rocky.views.tasks.client")
    mock_scheduler_client.get_lazy_task_list.return_value = lazy_task_list_with_boefje

    request = setup_request(rf.get("boefjes_task_list"), client_member.user)
    response = BoefjesTaskListView.as_view()(request, organization_code=client_member.organization.code)

    assertContains(response, "1b20f85f")
    assertContains(response, "Hostname|internet|mispo.es")

    mock_scheduler_client.get_lazy_task_list.assert_has_calls(
        [
            call(
                scheduler_id="boefje-test",
                task_type="boefje",
                status=None,
                min_created_at=None,
                max_created_at=None,
                input_ooi=None,
            )
        ]
    )


def test_tasks_view_error(rf, client_member, mocker, lazy_task_list_with_boefje):
    mock_scheduler_client = mocker.patch("rocky.views.tasks.client")
    mock_scheduler_client.get_lazy_task_list.return_value = lazy_task_list_with_boefje
    mock_scheduler_client.get_lazy_task_list.side_effect = HTTPError

    request = setup_request(rf.get("boefjes_task_list"), client_member.user)
    response = BoefjesTaskListView.as_view()(request, organization_code=client_member.organization.code)

    assertContains(response, "error")
    assertContains(response, "Fetching tasks failed")


def test_reschedule_task(rf, client_member, mocker, task):
    mock_scheduler_client = mocker.patch("rocky.views.tasks.client")
    mock_scheduler_client.get_task_details.return_value = task
    session = mocker.patch("tools.view_helpers.client.session")
    session.post.return_value = mocker.MagicMock()

    task_id = "e02c18dc-8013-421d-a86d-3a00f6019533"
    request = setup_request(
        rf.post(
            f"/en/{client_member.organization.code}/tasks/boefjes/?task_id={task_id}",
            data={"action": "reschedule_task"},
        ),
        client_member.user,
    )
    response = BoefjesTaskListView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 302
    assert list(request._messages)[0].message == (
        "Your task is scheduled and will soon be started in the background. "
        "Results will be added to the object list when they are in. "
        "It may take some time, a refresh of the page may be needed to show the results."
    )


def test_reschedule_task_already_queued(rf, client_member, mocker, task):
    mock_scheduler_client = mocker.patch("rocky.views.tasks.client")
    mock_scheduler_client.get_task_details.return_value = task
    session = mocker.patch("tools.view_helpers.client.session")
    mock_response = mocker.MagicMock()
    mock_response.status_code = HTTPStatus.TOO_MANY_REQUESTS
    return_value = mocker.MagicMock()
    return_value.raise_for_status.side_effect = HTTPError(response=mock_response)
    session.post.return_value = return_value

    task_id = "e02c18dc-8013-421d-a86d-3a00f6019533"
    request = setup_request(
        rf.post(
            f"/en/{client_member.organization.code}/tasks/boefjes/?task_id={task_id}",
            data={"action": "reschedule_task"},
        ),
        client_member.user,
    )
    response = BoefjesTaskListView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 302
    assert list(request._messages)[0].message == "Task queue is full, please try again later."
