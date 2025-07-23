import uuid

import pytest
from django.http import Http404

from openkat.views.task_detail import NormalizerTaskJSONView
from openkat.views.tasks import BoefjesTaskListView
from tests.conftest import setup_request


def test_get_task_details_json_bad_task_id(rf, client_member, mock_scheduler):
    request = setup_request(rf.get("normalizer_task_view"), client_member.user)

    with pytest.raises(Http404):
        NormalizerTaskJSONView.as_view()(
            request, organization_code=client_member.organization.code, task_id=uuid.uuid4()
        )


def test_reschedule_task_bad_task_id(rf, client_member, mock_scheduler):
    request = setup_request(
        rf.post("task_list", {"action": "reschedule_task", "task_id": uuid.uuid4()}), client_member.user
    )

    with pytest.raises(Http404):
        BoefjesTaskListView.as_view()(request, organization_code=client_member.organization.code)
