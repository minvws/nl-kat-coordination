from unittest.mock import call

import pytest
from django.http import Http404
from pytest_django.asserts import assertContains

from rocky.scheduler import SchedulerError, TooManyRequestsError
from rocky.views.bytes_raw import BytesRawView
from rocky.views.tasks import BoefjesTaskListView
from tests.conftest import setup_request


def test_boefjes_tasks(rf, client_member, mock_scheduler, lazy_task_list_empty):
    mock_scheduler.get_lazy_task_list.return_value = lazy_task_list_empty

    request = setup_request(rf.get("boefjes_task_list"), client_member.user)
    response = BoefjesTaskListView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 200

    mock_scheduler.get_lazy_task_list.assert_has_calls(
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


def test_tasks_view_simple(rf, client_member, mock_scheduler, lazy_task_list_with_boefje):
    mock_scheduler.get_lazy_task_list.return_value = lazy_task_list_with_boefje

    request = setup_request(rf.get("boefjes_task_list"), client_member.user)
    response = BoefjesTaskListView.as_view()(request, organization_code=client_member.organization.code)

    assertContains(response, "1b20f85f")
    assertContains(response, "Hostname|internet|mispo.es")

    mock_scheduler.get_lazy_task_list.assert_has_calls(
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
    mock_scheduler_client = mocker.patch("rocky.scheduler.get_scheduler")()
    mock_scheduler_client.get_lazy_task_list.return_value = lazy_task_list_with_boefje
    mock_scheduler_client.get_lazy_task_list.side_effect = SchedulerError

    request = setup_request(rf.get("boefjes_task_list"), client_member.user)
    response = BoefjesTaskListView.as_view()(request, organization_code=client_member.organization.code)

    assertContains(response, "error")
    assertContains(response, "Could not connect to Scheduler. Service is possibly down.")


def test_reschedule_task(rf, client_member, mock_scheduler, task):
    mock_scheduler.get_task_details.return_value = task

    request = setup_request(
        rf.post(
            f"/en/{client_member.organization.code}/tasks/boefjes/?task_id={task.id}",
            data={"action": "reschedule_task"},
        ),
        client_member.user,
    )
    response = BoefjesTaskListView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 302
    assert list(request._messages)[0].message == (
        "Task of "
        + task.type.title()
        + " "
        + task.p_item.data.boefje.name
        + " with input object "
        + task.p_item.data.input_ooi
        + " is scheduled and will soon be started in the background. "
        "Results will be added to the object list when they are in. "
        "It may take some time, a refresh of the page may be needed to show the results."
    )


def test_reschedule_task_already_queued(rf, client_member, mock_scheduler, mocker, task):
    mock_scheduler.get_task_details.return_value = task
    mock_scheduler.push_task.side_effect = TooManyRequestsError

    request = setup_request(
        rf.post(
            f"/en/{client_member.organization.code}/tasks/boefjes/?task_id={task.id}",
            data={"action": "reschedule_task"},
        ),
        client_member.user,
    )

    response = BoefjesTaskListView.as_view()(
        request,
        organization_code=client_member.organization.code,
    )

    assert response.status_code == 302

    assert (
        list(request._messages)[0].message
        == "Scheduling "
        + task.type.title()
        + " "
        + task.p_item.data.boefje.name
        + " with input object "
        + task.p_item.data.input_ooi
        + " failed. "
        "Task queue is full, please try again later."
    )


def test_reschedule_task_from_other_org(rf, client_member, client_member_b, mock_scheduler, task):
    mock_scheduler.get_task_details.return_value = task

    request = setup_request(
        rf.post(
            f"/en/{client_member.organization.code}/tasks/boefjes/?task_id={task.id}",
            data={"action": "reschedule_task"},
        ),
        client_member_b.user,
    )
    with pytest.raises(Http404):
        BoefjesTaskListView.as_view()(request, organization_code=client_member.organization.code)


def test_download_task_other_org_from_other_org_url(
    rf, client_member, client_member_b, mock_bytes_client, bytes_raw_metas
):
    with pytest.raises(Http404):
        BytesRawView.as_view()(
            setup_request(rf.get("bytes_raw"), client_member.user),
            organization_code=client_member_b.organization.code,
            boefje_meta_id=bytes_raw_metas[0]["id"],
        )


def test_download_task_same_org(rf, client_member, mock_bytes_client, bytes_raw_metas, bytes_get_raw):
    mock_bytes_client().get_raw.return_value = bytes_get_raw
    mock_bytes_client().get_raw_metas.return_value = bytes_raw_metas

    request = setup_request(rf.get("bytes_raw"), client_member.user)

    response = BytesRawView.as_view()(
        request,
        organization_code=client_member.organization.code,
        boefje_meta_id=bytes_raw_metas[0]["id"],
    )

    assert response.status_code == 200


def test_download_task_forbidden(rf, client_member, mock_bytes_client, bytes_raw_metas):
    mock_bytes_client().get_raw_metas.side_effect = Http404

    request = setup_request(rf.get("bytes_raw"), client_member.user)

    response = BytesRawView.as_view()(
        request,
        organization_code=client_member.organization.code,
        boefje_meta_id=bytes_raw_metas[0]["id"],
    )

    assert response.status_code == 302
    assert list(request._messages)[0].message == "Getting raw data failed."
