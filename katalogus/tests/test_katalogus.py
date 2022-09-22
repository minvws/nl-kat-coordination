import uuid
from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, TestCase
from django.urls import reverse
from octopoes.models import Reference, InheritedScanProfile
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.types import (
    DNSARecord,
    DNSAAAARecord,
    DNSTXTRecord,
)
from rocky.scheduler import QueuePrioritizedItem, Boefje, BoefjeTask
from rocky.views import BoefjeDetailView
from tools.models import Organization, SCAN_LEVEL

UUIDS = [uuid.uuid4() for _ in range(10)]
User = get_user_model()


class KATalogusTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="admin@openkat.nl", password="TestTest123!!"
        )
        cls.organization = Organization.objects.create(name="Development", code="_dev")

    def setUp(self):
        self.factory = RequestFactory()
        self.boefje_detail = BoefjeDetailView.as_view()
        self.katalogus_boefje = Boefje(
            id="dns-records",
            name="DnsRecords",
            repository_id="LOCAL",
            description="Fetch the DNS record(s) of a hostname",
            scan_level=SCAN_LEVEL.L1,
            consumes={Hostname},
            produces={
                DNSARecord,
                DNSAAAARecord,
                DNSTXTRecord,
            },
        )

        self.scheduled_boefje = Boefje(
            id="dns-records",
            name="DnsRecords",
            repository_id="LOCAL",
            description="Fetch the DNS record(s) of a hostname",
            scan_level=1,
            version=None,
            consumes={"Hostname"},
            produces={
                "DNSARecord",
                "DNSAAAARecord",
                "DNSTXTRecord",
            },
        )

    @patch("rocky.views.boefje.uuid4", side_effect=UUIDS)
    @patch("rocky.views.boefje.client")
    @patch("rocky.views.boefje.get_katalogus")
    def test_schedule_boefjes(
        self,
        mock_get_katalogus: MagicMock,
        mock_scheduler_client: MagicMock,
        _: MagicMock,
    ):

        input_ooi = Hostname(
            network=Reference.from_str("Network|internet"),
            name="example.com",
            scan_profile=InheritedScanProfile(
                reference=Reference.from_str("Network|internet|example.com"), level=1
            ),
        )

        # Setup mocks
        octopoes_mock = MagicMock()
        octopoes_mock.get.return_value = input_ooi

        mock_get_katalogus().get_boefje.return_value = self.katalogus_boefje
        mock_get_katalogus().get_description.return_value = ""

        # Build post request
        post_data = {"action": "scan", "ooi": "Hostname|internet|example.com"}
        kwargs = {"id": "dns-records"}
        request = self.factory.post(
            reverse("katalogus_detail", kwargs=kwargs), post_data
        )
        request.user = self.user
        request.user.is_verified = lambda: True
        request.session = "session"
        request.active_organization = self.organization
        request.octopoes_api_connector = octopoes_mock

        request._messages = FallbackStorage(request)

        # Execute
        self.boefje_detail(request, **kwargs)

        # Verify
        mock_scheduler_client.push_task.assert_called_once_with(
            "boefje-_dev",
            QueuePrioritizedItem(
                priority=1,
                item=BoefjeTask(
                    id=UUIDS[0].hex,
                    boefje=self.scheduled_boefje,
                    input_ooi=Reference.from_str("Hostname|internet|example.com"),
                    organization="_dev",
                ),
            ),
        )
