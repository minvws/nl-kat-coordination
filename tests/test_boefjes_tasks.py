import pytest
from django.http import Http404
from pytest_django.asserts import assertContains

from files.models import File, PluginContent
from openkat.views.bytes_raw import BytesRawView
from openkat.views.tasks import BoefjesTaskListView
from tests.conftest import setup_request


def test_boefjes_tasks(rf, client_member, mock_scheduler):
    request = setup_request(rf.get("boefjes_task_list"), client_member.user)
    response = BoefjesTaskListView.as_view()(
        request,
        organization_code=client_member.organization.code,
        scheduler_id="boefje-test",
        task_type="boefje",
        status=None,
        min_created_at=None,
        max_created_at=None,
        input_ooi=None,
    )

    assert response.status_code == 200


def test_tasks_view_simple(rf, client_member, mock_scheduler):
    request = setup_request(rf.get("boefjes_task_list"), client_member.user)
    response = BoefjesTaskListView.as_view()(request, organization_code=client_member.organization.code)

    assertContains(response, "Completed")


def test_reschedule_task(rf, client_member, mock_scheduler, task_db):
    request = setup_request(
        rf.post(
            f"/en/{client_member.organization.code}/tasks/boefjes/",
            data={"action": "reschedule_task", "task_id": task_db.id},
        ),
        client_member.user,
    )
    response = BoefjesTaskListView.as_view()(request, organization_code=client_member.organization.code)

    assert response.status_code == 200
    assert list(request._messages)[0].message == (
        "Your task is scheduled and will soon be started in the background. "
        "Results will be added to the object list when they are in. "
        "It may take some time, a refresh of the page may be needed to show the results."
    )


def test_reschedule_task_from_other_org(rf, client_member, client_member_b, mock_scheduler, task_db):
    request = setup_request(
        rf.post(
            f"/en/{client_member.organization.code}/tasks/boefjes/",
            data={"action": "reschedule_task", "task_id": task_db.id},
        ),
        client_member_b.user,
    )
    with pytest.raises(Http404):
        BoefjesTaskListView.as_view()(request, organization_code=client_member.organization.code)


def test_download_task_other_org_from_other_org_url(rf, client_member, organization_b):
    with pytest.raises(Http404):
        BytesRawView.as_view()(
            setup_request(rf.get("bytes_raw"), client_member.user),
            organization_code=organization_b.code,
            boefje_meta_id="85c01c8c-c0bf-4fe8-bda5-abdf2d03117c",
        )


def test_download_task_same_org(rf, client_member, bytes_raw_metas, bytes_get_raw):
    raw = File.objects.create(file=PluginContent(bytes_get_raw, "test"))
    request = setup_request(rf.get("bytes_raw"), client_member.user)

    response = BytesRawView.as_view()(request, organization_code=client_member.organization.code, boefje_meta_id=raw.id)

    assert response.status_code == 200
