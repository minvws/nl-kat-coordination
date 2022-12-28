from unittest.mock import call

from django.contrib.messages.storage.fallback import FallbackStorage
from django.urls import reverse
from requests import HTTPError

from pytest_django.asserts import assertContains

from rocky.scheduler import PaginatedTasksResponse
from rocky.views import TASK_LIMIT, BoefjesTaskListView


def test_boefjes_tasks(rf, user, organization, mocker):
    mock_scheduler_client = mocker.patch("rocky.views.tasks.client")
    mock_scheduler_client.list_tasks.return_value = PaginatedTasksResponse.parse_obj(
        {"count": 0, "next": None, "previous": None, "results": []}
    )

    request = rf.get(reverse("boefjes_task_list"))
    request.user = user
    request.active_organization = organization

    response = BoefjesTaskListView.as_view()(request)

    assert response.status_code == 200

    mock_scheduler_client.list_tasks.assert_has_calls([call(f"boefje-{organization.code}", limit=TASK_LIMIT)])


def test_tasks_view_simple(rf, user, organization, mocker):
    mock_scheduler_client = mocker.patch("rocky.views.tasks.client")
    mock_scheduler_client.list_tasks.return_value = PaginatedTasksResponse.parse_raw(
        """
    {
        "count": 1,
        "next": null,
        "previous": null,
        "results": [
            {
                "id": "1b20f85f-63d5-4baa-be9e-f3f19d6e3fae",
                "hash": "19ed51514b37d42f79c5e95469956b05",
                "scheduler_id": "boefje-_dev",
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
                            "repository_id": null,
                            "version": null,
                            "scan_level": 1,
                            "consumes": [
                                "Hostname"
                            ],
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
                                "NXDOMAIN"
                            ]
                        },
                        "input_ooi": "Hostname|internet|mispo.es.",
                        "organization": "_dev"
                    }
                },
                "status": "completed",
                "created_at": "2022-08-09 11:53:41.378292",
                "modified_at": "2022-08-09 11:54:21.002838"
            }
        ]
    }
    """
    )

    request = rf.get(reverse("task_list"))
    request.user = user
    request.active_organization = organization

    response = BoefjesTaskListView.as_view()(request)

    assertContains(response, "1b20f85f")
    assertContains(response, "Hostname|internet|mispo.es.")

    mock_scheduler_client.list_tasks.assert_has_calls([call(f"boefje-{organization.code}", limit=TASK_LIMIT)])


def test_tasks_view_no_organization(rf, user):
    request = rf.get(reverse("task_list"))
    request.user = user
    request.active_organization = None
    request.session = "session"
    request._messages = FallbackStorage(request)

    response = BoefjesTaskListView.as_view()(request)

    assertContains(response, "error")
    assertContains(response, "Organization could not be found")


def test_tasks_view_error(rf, user, organization, mocker):
    mock_scheduler_client = mocker.patch("rocky.views.tasks.client")
    mock_scheduler_client.list_tasks.side_effect = HTTPError

    request = rf.get(reverse("task_list"))
    request.user = user
    request.active_organization = organization
    request.session = "session"
    request._messages = FallbackStorage(request)

    response = BoefjesTaskListView.as_view()(request)

    assertContains(response, "error")
    assertContains(response, "Fetching tasks failed")
