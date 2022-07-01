import uuid
from unittest.mock import patch, MagicMock

from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.test import TestCase
from django.urls import reverse

from rocky.flower import FlowerException
from rocky.views.tasks import task_list, TASKS_LIMIT
from tools.models import Organization, Job

User = get_user_model()

UUIDS = [uuid.uuid4() for _ in range(10)]


@patch("rocky.views.tasks.FlowerClient")
class TasksTestCase(TestCase):
    user = None
    organization = None
    job1 = None

    @classmethod
    def setUpTestData(cls):
        cls.factory = RequestFactory()
        cls.user = User.objects.create_user("admin")
        cls.organization = Organization.objects.create(name="Development", code="_dev")
        cls.job1 = Job.objects.create(
            id=UUIDS[0],
            organization=cls.organization,
            boefje_id="kat_test.scan",
            arguments={"key": "value"},
        )
        cls.job1.save()

    def test_tasks_view(self, mock_flower_client: MagicMock):
        mock_flower_client().get_tasks.return_value = {}

        request = self.factory.get(reverse("task_list"))
        request.user = self.user
        request.user.is_verified = lambda: True
        request.active_organization = self.organization

        response = task_list(request)

        mock_flower_client().get_tasks.assert_called_once_with(
            "tasks.handle_boefje", limit=TASKS_LIMIT
        )

    def test_tasks_view_simple(self, mock_flower_client: MagicMock):
        job_id = str(UUIDS[0])
        mock_flower_client().get_tasks.return_value = {
            job_id: {
                "uuid": job_id,
                "name": "tasks.handle_boefje",
                "state": "SUCCESS",
                "received": 1636466183.8427753,
                "sent": None,
                "started": 1636466183.843239,
                "rejected": None,
                "succeeded": 1636466184.5156317,
                "failed": None,
                "retried": None,
                "revoked": None,
                "kwargs": "{}",
                "eta": None,
                "expires": None,
                "retries": 0,
                "result": "None",
                "exception": None,
                "timestamp": 1636466184.5156317,
                "runtime": 0.6714699999993172,
            }
        }

        request = self.factory.get(reverse("task_list"))
        request.user = self.user
        request.user.is_verified = lambda: True
        request.active_organization = self.organization

        response = task_list(request)

        self.assertContains(response, job_id)

        mock_flower_client().get_tasks.assert_called_once_with(
            "tasks.handle_boefje", limit=TASKS_LIMIT
        )

    def test_tasks_view_no_organization(self, mock_flower_client: MagicMock):
        job_id = UUIDS[0]
        mock_flower_client().get_tasks.return_value = {
            str(job_id): {"name": "boefje", "uuid": str(job_id), "state": "received"}
        }

        request = self.factory.get(reverse("task_list"))
        request.user = self.user
        request.user.is_verified = lambda: True
        request.active_organization = None

        response = task_list(request)

        self.assertNotContains(response, job_id)

        mock_flower_client().get_tasks.assert_called_once_with(
            "tasks.handle_boefje", limit=TASKS_LIMIT
        )

    def test_tasks_view_error(self, mock_flower_client: MagicMock):
        mock_flower_client().get_tasks.side_effect = FlowerException

        request = self.factory.get(reverse("task_list"))
        request.user = self.user
        request.user.is_verified = lambda: True
        request.active_organization = self.organization

        response = task_list(request)

        self.assertContains(response, "error")
