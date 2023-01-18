from unittest.mock import call

from django.contrib.messages.storage.fallback import FallbackStorage
from django.urls import reverse
from pytest_django.asserts import assertContains
from requests import HTTPError

from rocky.views.tasks import BoefjesTaskListView


def test_boefjes_tasks(rf, my_user, organization, mocker, lazy_task_list_empty):
    mock_scheduler_client = mocker.patch("rocky.views.tasks.client")
    mock_scheduler_client.get_lazy_task_list.return_value = lazy_task_list_empty

    kwargs = {"organization_code": organization.code}
    request = rf.get(reverse("boefjes_task_list", kwargs=kwargs))
    request.user = my_user
    request.organization = organization

    response = BoefjesTaskListView.as_view()(request, **kwargs)

    assert response.status_code == 200

    mock_scheduler_client.get_lazy_task_list.assert_has_calls(
        [
            call(
                scheduler_id="boefje-test",
                object_type="boefje",
                status=None,
                min_created_at=None,
                max_created_at=None,
            )
        ]
    )


def test_tasks_view_simple(rf, my_user, organization, mocker, lazy_task_list_with_boefje):
    mock_scheduler_client = mocker.patch("rocky.views.tasks.client")
    mock_scheduler_client.get_lazy_task_list.return_value = lazy_task_list_with_boefje

    kwargs = {"organization_code": organization.code}
    request = rf.get(reverse("boefjes_task_list", kwargs=kwargs))
    request.user = my_user
    request.organization = organization

    response = BoefjesTaskListView.as_view()(request, **kwargs)

    assertContains(response, "1b20f85f")
    assertContains(response, "Hostname|internet|mispo.es.")

    mock_scheduler_client.get_lazy_task_list.assert_has_calls(
        [
            call(
                scheduler_id="boefje-test",
                object_type="boefje",
                status=None,
                min_created_at=None,
                max_created_at=None,
            )
        ]
    )


def test_tasks_view_error(rf, my_user, organization, mocker, lazy_task_list_with_boefje):
    mock_scheduler_client = mocker.patch("rocky.views.tasks.client")
    mock_scheduler_client.get_lazy_task_list.return_value = lazy_task_list_with_boefje
    mock_scheduler_client.get_lazy_task_list.side_effect = HTTPError

    kwargs = {"organization_code": organization.code}
    request = rf.get(reverse("boefjes_task_list", kwargs=kwargs))
    request.user = my_user
    request.organization = organization

    request.session = "session"
    request._messages = FallbackStorage(request)

    response = BoefjesTaskListView.as_view()(request, **kwargs)

    assertContains(response, "error")
    assertContains(response, "Fetching tasks failed")
