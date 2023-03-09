import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.middleware import OTPMiddleware
from octopoes.models import DeclaredScanProfile, ScanLevel, Reference
from octopoes.models.ooi.findings import Finding
from octopoes.models.ooi.network import Network
from rocky.scheduler import Task
from tools.models import OOIInformation, OrganizationMember
from tests.setup import OrganizationSetup, UserSetup, MemberSetup


@pytest.fixture
def organization():
    return OrganizationSetup().create_organization()


@pytest.fixture
def organization_b():
    return OrganizationSetup("OrganizationB", "org_b").create_organization()


@pytest.fixture
def superuser(django_user_model):
    return UserSetup(django_user_model, email="superuser@openkat.nl", password="SuperSuper123!!")._create_superuser()


@pytest.fixture
def superuser_member(superuser, organization):
    return MemberSetup(superuser, organization).create_member()


@pytest.fixture
def superuser_member_b(django_user_model, organization_b):
    superuser_b = UserSetup(
        django_user_model, email="superuserB@openkat.nl", password="SuperBSuperB123!!"
    )._create_superuser()
    return MemberSetup(superuser_b, organization_b).create_member()


@pytest.fixture
def adminuser(django_user_model):
    return UserSetup(django_user_model, email="admin@openkat.nl", password="AdminAdmin123!!")._create_admin_user()


@pytest.fixture
def admin_member(adminuser, organization):
    return MemberSetup(adminuser, organization).create_member()


@pytest.fixture
def admin_member_b(django_user_model, organization_b):
    admin_user_b = UserSetup(
        django_user_model, email="adminB@openkat.nl", password="AdminBAdminB123!!"
    )._create_admin_user()
    return MemberSetup(admin_user_b, organization_b).create_member()


@pytest.fixture
def redteamuser(django_user_model):
    return UserSetup(
        django_user_model, email="redteamer@openkat.nl", password="RedteamRedteam123!!"
    )._create_redteam_user()


@pytest.fixture
def redteam_member(redteamuser, organization):
    return MemberSetup(redteamuser, organization).create_member()


@pytest.fixture
def redteam_member_b(django_user_model, organization_b):
    redteam_user_b = UserSetup(
        django_user_model, email="redteamerB@openkat.nl", password="RedteamBRedteamB123!!"
    )._create_redteam_user()
    return MemberSetup(redteam_user_b, organization_b).create_member()


@pytest.fixture
def clientuser(django_user_model):
    return UserSetup(django_user_model, email="client@openkat.nl", password="ClientClient123!!")._create_client_user()


@pytest.fixture
def client_member(clientuser, organization):
    return MemberSetup(clientuser, organization).create_member()


@pytest.fixture
def client_member_b(django_user_model, organization_b):
    client_user_b = UserSetup(
        django_user_model, email="clientB@openkat.nl", password="ClientBClientB123!!"
    )._create_client_user()
    return MemberSetup(client_user_b, organization_b).create_member()


@pytest.fixture
def my_new_user(django_user_model, organization):
    user = UserSetup(
        django_user_model, full_name="New user", email="cl1@openkat.nl", password="TestTest123!!"
    )._create_superuser()
    member = MemberSetup(user, organization).create_member()
    member.status = OrganizationMember.STATUSES.NEW
    member.save()
    return member


@pytest.fixture
def my_blocked_user(django_user_model, organization):
    user = UserSetup(
        django_user_model, full_name="Blocked user", email="cl2@openkat.nl", password="TestTest123!!"
    )._create_superuser()
    member = MemberSetup(user, organization).create_member()
    member.status = OrganizationMember.STATUSES.BLOCKED
    member.save()
    return member


@pytest.fixture
def mock_models_katalogus(mocker):
    return mocker.patch("tools.models.get_katalogus")


@pytest.fixture
def mock_views_katalogus(mocker):
    return mocker.patch("rocky.views.ooi_report.get_katalogus")


@pytest.fixture
def mock_bytes_client(mocker):
    return mocker.patch("rocky.bytes_client.BytesClient")


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
def finding():
    return Finding(
        finding_type=Reference.from_str("KATFindingType|KAT-0001"),
        ooi=Reference.from_str("Network|testnetwork"),
        proof="proof",
        description="description",
        reproduce="reproduce",
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


def get_boefjes_data():
    return json.loads((Path(__file__).parent / "stubs" / "katalogus_boefjes.json").read_text())
