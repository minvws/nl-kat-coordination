from unittest.mock import call, MagicMock

import pytest
from django.contrib.messages.storage.fallback import FallbackStorage
from django.urls import reverse
from pytest_django.asserts import assertContains
from requests import HTTPError

from rocky.scheduler import Task
from rocky.views import BoefjesTaskListView


@pytest.fixture
def lazy_task_list_empty() -> MagicMock:
    mock = MagicMock()
    mock.__getitem__.return_value = []
    mock.count.return_value = 0
    return mock


@pytest.fixture
def lazy_task_list_with_boefje() -> MagicMock:
    mock = MagicMock()
    mock.__getitem__.return_value = [
        Task.parse_obj(
            {
                "id": "1b20f85f-63d5-4baa-be9e-f3f19d6e3fae",
                "hash": "19ed51514b37d42f79c5e95469956b05",
                "scheduler_id": "boefje-test",
                "type": "boefje",
                "p_item": {
                    "id": "1b20f85f-63d5-4baa-be9e-f3f19d6e3fae",
                    "hash": "19ed51514b37d42f79c5e95469956b05",
                    "priority": 1,
                    "data": {
                        "id": "1b20f85f63d54baabe9ef3f19d6e3fae",
                        "boefje": {
                            "id": "dns-records",
                            "name": "DnsRecords",
                            "description": "Fetch the DNS record(s) of a hostname",
                            "repository_id": None,
                            "version": None,
                            "scan_level": 1,
                            "consumes": ["Hostname"],
                            "produces": [
                                "DNSNSRecord",
                                "DNSARecord",
                                "DNSCNAMERecord",
                                "DNSMXRecord",
                                "DNSZone",
                                "Hostname",
                                "DNSAAAARecord",
                                "IPAddressV4",
                                "DNSSOARecord",
                                "DNSTXTRecord",
                                "IPAddressV6",
                                "Network",
                                "NXDOMAIN",
                            ],
                        },
                        "input_ooi": "Hostname|internet|mispo.es.",
                        "organization": "_dev",
                    },
                },
                "status": "completed",
                "created_at": "2022-08-09 11:53:41.378292",
                "modified_at": "2022-08-09 11:54:21.002838",
            }
        )
    ]
    mock.count.return_value = 1
    return mock


def test_boefjes_tasks(rf, user, organization, mocker, lazy_task_list_empty):
    mock_scheduler_client = mocker.patch("rocky.views.tasks.client")
    mock_scheduler_client.get_lazy_task_list.return_value = lazy_task_list_empty

    request = rf.get(reverse("boefjes_task_list"))
    request.user = user
    request.active_organization = organization

    response = BoefjesTaskListView.as_view()(request)

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


def test_tasks_view_simple(rf, user, organization, mocker, lazy_task_list_with_boefje):
    mock_scheduler_client = mocker.patch("rocky.views.tasks.client")
    mock_scheduler_client.get_lazy_task_list.return_value = lazy_task_list_with_boefje

    request = rf.get(reverse("task_list"))
    request.user = user
    request.active_organization = organization

    response = BoefjesTaskListView.as_view()(request)

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


def test_tasks_view_no_organization(rf, user):
    request = rf.get(reverse("task_list"))
    request.user = user
    request.active_organization = None
    request.session = "session"
    request._messages = FallbackStorage(request)

    response = BoefjesTaskListView.as_view()(request)

    assertContains(response, "error")
    assertContains(response, "Organization could not be found")


def test_tasks_view_error(rf, user, organization, mocker, lazy_task_list_with_boefje):
    mock_scheduler_client = mocker.patch("rocky.views.tasks.client")
    mock_scheduler_client.get_lazy_task_list.return_value = lazy_task_list_with_boefje
    mock_scheduler_client.get_lazy_task_list.side_effect = HTTPError

    request = rf.get(reverse("task_list"))
    request.user = user
    request.active_organization = organization
    request.session = "session"
    request._messages = FallbackStorage(request)

    response = BoefjesTaskListView.as_view()(request)

    assertContains(response, "error")
    assertContains(response, "Fetching tasks failed")
