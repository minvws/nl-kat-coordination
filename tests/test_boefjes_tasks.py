import uuid
from unittest.mock import MagicMock, patch, call

from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, TestCase
from django.urls import reverse
from requests import HTTPError

from rocky.scheduler import PaginatedTasksResponse
from rocky.views import BoefjesTaskListView, TASK_LIMIT
from tools.models import Organization

UUIDS = [uuid.uuid4() for _ in range(10)]
User = get_user_model()


@patch("rocky.views.tasks.client")
class TaskListTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.factory = RequestFactory()
        cls.user = User.objects.create_user(
            email="admin@openkat.nl", password="TestTest123!!"
        )
        cls.organization = Organization.objects.create(name="Development", code="_dev")
        cls.task_list = BoefjesTaskListView.as_view()

    def test_boefjes_tasks(self, mock_scheduler_client: MagicMock):
        mock_scheduler_client.list_tasks.return_value = (
            PaginatedTasksResponse.parse_obj(
                {"count": 0, "next": None, "previous": None, "results": []}
            )
        )

        request = self.factory.get(reverse("boefjes_task_list"))
        request.user = self.user
        request.user.is_verified = lambda: True
        request.active_organization = self.organization

        _ = self.task_list(request)

        mock_scheduler_client.list_tasks.assert_has_calls(
            [call("boefje-_dev", limit=TASK_LIMIT)]
        )

    def test_tasks_view_simple(self, mock_scheduler_client: MagicMock):
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
                    "task": {
                        "priority": 1,
                        "item": {
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

        request = self.factory.get(reverse("task_list"))
        request.user = self.user
        request.user.is_verified = lambda: True
        request.active_organization = self.organization

        response = self.task_list(request)

        self.assertContains(response, "1b20f85f")
        self.assertContains(response, "Hostname|internet|mispo.es.")

        mock_scheduler_client.list_tasks.assert_has_calls(
            [call("boefje-_dev", limit=TASK_LIMIT)]
        )

    def test_tasks_view_no_organization(self, _: MagicMock):
        request = self.factory.get(reverse("task_list"))
        request.user = self.user
        request.user.is_verified = lambda: True
        request.active_organization = None
        setattr(request, "session", "session")
        request._messages = FallbackStorage(request)

        response = self.task_list(request)

        self.assertContains(response, "error")
        self.assertContains(response, "Organization could not be found")

    def test_tasks_view_error(self, mock_scheduler_client: MagicMock):
        mock_scheduler_client.list_tasks.side_effect = HTTPError

        request = self.factory.get(reverse("task_list"))
        request.user = self.user
        request.user.is_verified = lambda: True
        request.active_organization = self.organization
        setattr(request, "session", "session")
        request._messages = FallbackStorage(request)

        response = self.task_list(request)

        self.assertContains(response, "error")
        self.assertContains(response, "Fetching tasks failed")
