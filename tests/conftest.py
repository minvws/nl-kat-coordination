from unittest.mock import patch, MagicMock

import pytest
from django.contrib.auth.models import Permission, ContentType, Group
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.middleware import OTPMiddleware

from octopoes.models import DeclaredScanProfile, ScanLevel, Reference
from octopoes.models.ooi.network import Network
from rocky.scheduler import Task
from tools.models import Organization, OrganizationMember, OOIInformation, Indemnification
from tools.models import GROUP_REDTEAM, GROUP_ADMIN


@pytest.fixture
def organization():
    with patch("katalogus.client.KATalogusClientV1"), patch(
        "octopoes.connector.octopoes.OctopoesAPIConnector.create_node"
    ):
        organization = Organization.objects.create(name="Test Organization", code="test")
    return organization


@pytest.fixture
def user(django_user_model):
    user = django_user_model.objects.create_superuser(email="admin@openkat.nl", password="TestTest123!!")
    user.is_verified = lambda: True

    device = user.staticdevice_set.create(name="default")
    device.token_set.create(token=user.get_username())

    return user


@pytest.fixture
def my_user(user, organization):
    OrganizationMember.objects.create(
        user=user,
        organization=organization,
        verified=True,
        authorized=True,
        status=OrganizationMember.STATUSES.ACTIVE,
        trusted_clearance_level=4,
        acknowledged_clearance_level=4,
    )
    content_type = ContentType.objects.get_by_natural_key("tools", "organizationmember")
    permission, _ = Permission.objects.get_or_create(
        content_type=content_type,
        codename="can_scan_organization",
    )
    Indemnification.objects.create(
        organization=organization,
        user=user,
    )
    user.user_permissions.add(permission)

    return user


@pytest.fixture
def my_red_teamer(my_user, organization):
    group = Group.objects.create(name=GROUP_ADMIN)
    group.user_set.add(my_user)

    group = Group.objects.create(name=GROUP_REDTEAM)
    group.user_set.add(my_user)

    return my_user


@pytest.fixture
def mock_models_katalogus(mocker):
    return mocker.patch("tools.models.get_katalogus")


@pytest.fixture
def mock_views_katalogus(mocker):
    return mocker.patch("rocky.views.ooi_report.get_katalogus")


@pytest.fixture
def mock_models_octopoes(mocker):
    return mocker.patch("tools.models.OctopoesAPIConnector")


@pytest.fixture
def mock_organization_view_octopoes(mocker):
    return mocker.patch("account.mixins.OctopoesAPIConnector")


@pytest.fixture
def mock_crisis_room_octopoes(mocker):
    return mocker.patch("crisis_room.views.OctopoesAPIConnector")


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
                            "id": "test-boefje",
                            "name": "TestBoefje",
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


@pytest.fixture
def network():
    return Network(
        name="testnetwork",
        scan_profile=DeclaredScanProfile(reference=Reference.from_str("Network|testnetwork"), level=ScanLevel.L1),
    )


@pytest.fixture
def plugin_details():
    return {
        "id": "test-boefje",
        "type": "boefje",
        "name": "TestBoefje",
        "description": "Meows to the moon",
        "repository_id": "test-repository",
        "scan_level": 1,
        "consumes": ["Network"],
        "produces": ["Network"],
        "enabled": True,
    }


@pytest.fixture
def plugin_schema():
    return {
        "title": "Arguments",
        "type": "object",
        "properties": {
            "TEST_PROPERTY": {
                "title": "TEST_PROPERTY",
                "maxLength": 128,
                "type": "string",
                "description": "Test description",
            }
        },
        "required": ["TEST_PROPERTY"],
    }


@pytest.fixture
def ooi_information() -> OOIInformation:
    data = {"description": "Fake description...", "recommendation": "Fake recommendation...", "risk": "Low"}
    ooi_information = OOIInformation.objects.create(id="KATFindingType|KAT-000", data=data, consult_api=False)
    return ooi_information


def setup_request(request, user):
    request = SessionMiddleware(lambda r: r)(request)
    request.session[DEVICE_ID_SESSION_KEY] = user.staticdevice_set.get().persistent_id
    request = OTPMiddleware(lambda r: r)(request)
    request = MessageMiddleware(lambda r: r)(request)

    request.user = user

    return request


@pytest.fixture
def mock_scheduler(mocker):
    return mocker.patch("rocky.views.ooi_detail.scheduler.client")
