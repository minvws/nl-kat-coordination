from rocky.scheduler import SchedulerConnectError, SchedulerTooManyRequestError, SchedulerValidationError
from rocky.views.tasks import BoefjesTaskListView
from tests.conftest import setup_request


def test_tasks_view_connect_error(rf, client_member, mock_scheduler):
    mock_scheduler.list_tasks.side_effect = SchedulerConnectError

    request = setup_request(rf.get("boefjes_task_list"), client_member.user)
    response = BoefjesTaskListView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 302

    assert list(request._messages)[0].message == "Could not connect to Scheduler. Service is possibly down."


def test_tasks_view_validation_error(rf, client_member, mock_scheduler):
    mock_scheduler.list_tasks.side_effect = SchedulerValidationError

    request = setup_request(rf.get("boefjes_task_list"), client_member.user)
    response = BoefjesTaskListView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 302

    assert list(request._messages)[0].message == "Your request could not be validated."


def test_tasks_view_too_many_requests_error(rf, client_member, mock_scheduler):
    mock_scheduler.list_tasks.side_effect = SchedulerTooManyRequestError

    request = setup_request(rf.get("boefjes_task_list"), client_member.user)
    response = BoefjesTaskListView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 302

    assert (
        list(request._messages)[0].message
        == "Scheduler is receiving too many requests. Increase SCHEDULER_PQ_MAXSIZE or wait for task to finish."
    )
