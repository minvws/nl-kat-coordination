import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest
import binascii
from os import urandom
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.middleware import OTPMiddleware
from octopoes.models import DeclaredScanProfile, ScanLevel, Reference
from octopoes.models.ooi.findings import Finding
from octopoes.models.ooi.network import Network
from rocky.scheduler import Task
from unittest.mock import patch
from tools.models import OOIInformation, Organization, OrganizationMember, Indemnification
from django.contrib.auth.models import Permission, Group
from tools.models import GROUP_REDTEAM, GROUP_ADMIN, GROUP_CLIENT


def create_user(django_user_model, email, password, name, device_name, superuser=False):
    user = django_user_model.objects.create_user(email=email, password=password)
    user.full_name = name
    user.is_verified = lambda: True
    user.is_superuser = superuser
    user.save()
    device = user.staticdevice_set.create(name=device_name)
    device.token_set.create(token=binascii.hexlify(urandom(8)).decode())
    return user


def create_organization(name, organization_code):
    katalogus_client = "katalogus.client.KATalogusClientV1"
    octopoes_node = "tools.models.OctopoesAPIConnector"
    with patch(katalogus_client), patch(octopoes_node):
        return Organization.objects.create(name=name, code=organization_code)


def create_member(user, organization):
    Indemnification.objects.create(
        user=user,
        organization=organization,
    )

    return OrganizationMember.objects.create(
        user=user,
        organization=organization,
        status=OrganizationMember.STATUSES.ACTIVE,
        trusted_clearance_level=4,
        acknowledged_clearance_level=4,
        onboarded=False,
    )


def add_admin_group_permissions(member):
    group, _ = Group.objects.get_or_create(name=GROUP_ADMIN)
    member.groups.add(group)
    admin_permissions = [
        Permission.objects.get(codename="view_organization").id,
        Permission.objects.get(codename="view_organizationmember").id,
        Permission.objects.get(codename="add_organizationmember").id,
        Permission.objects.get(codename="change_organization").id,
        Permission.objects.get(codename="change_organizationmember").id,
    ]
    group.permissions.set(admin_permissions)


def add_redteam_group_permissions(member):
    group, _ = Group.objects.get_or_create(name=GROUP_REDTEAM)
    member.groups.add(group)
    redteam_permissions = [
        Permission.objects.get(codename="can_scan_organization").id,
        Permission.objects.get(codename="can_enable_disable_boefje").id,
        Permission.objects.get(codename="can_set_clearance_level").id,
    ]
    group.permissions.set(redteam_permissions)


def add_client_group(member):
    group, _ = Group.objects.get_or_create(name=GROUP_CLIENT)
    member.groups.add(group)


@pytest.fixture
def organization():
    return create_organization("Test Organization", "test")


@pytest.fixture
def organization_b():
    return create_organization("OrganizationB", "org_b")


@pytest.fixture
def superuser(django_user_model):
    return create_user(
        django_user_model, "superuser@openkat.nl", "SuperSuper123!!", "Superuser name", "default", superuser=True
    )


@pytest.fixture
def superuser_b(django_user_model):
    return create_user(
        django_user_model, "superuserB@openkat.nl", "SuperBSuperB123!!", "Superuser B name", "default_b", superuser=True
    )


@pytest.fixture
def superuser_member(superuser, organization):
    return create_member(superuser, organization)


@pytest.fixture
def superuser_member_b(superuser_b, organization_b):
    return create_member(superuser_b, organization_b)


@pytest.fixture
def adminuser(django_user_model):
    return create_user(django_user_model, "admin@openkat.nl", "AdminAdmin123!!", "Admin name", "default_admin")


@pytest.fixture
def adminuser_b(django_user_model):
    return create_user(django_user_model, "adminB@openkat.nl", "AdminBAdminB123!!", "Admin B name", "default_admin_b")


@pytest.fixture
def admin_member(adminuser, organization):
    member = create_member(adminuser, organization)
    add_admin_group_permissions(member)
    return member


@pytest.fixture
def admin_member_b(adminuser_b, organization_b):
    member = create_member(adminuser_b, organization_b)
    add_admin_group_permissions(member)
    return member


@pytest.fixture
def redteamuser(django_user_model):
    return create_user(
        django_user_model, "redteamer@openkat.nl", "RedteamRedteam123!!", "Redteam name", "default_redteam"
    )


@pytest.fixture
def redteamuser_b(django_user_model):
    return create_user(
        django_user_model, "redteamerB@openkat.nl", "RedteamBRedteamB123!!", "Redteam B name", "default_redteam_b"
    )


@pytest.fixture
def redteam_member(redteamuser, organization):
    member = create_member(redteamuser, organization)
    add_redteam_group_permissions(member)
    return member


@pytest.fixture
def redteam_member_b(redteamuser_b, organization_b):
    member = create_member(redteamuser_b, organization_b)
    add_redteam_group_permissions(member)
    return member


@pytest.fixture
def clientuser(django_user_model):
    return create_user(django_user_model, "client@openkat.nl", "ClientClient123!!", "Client name", "default_client")


@pytest.fixture
def clientuser_b(django_user_model):
    return create_user(
        django_user_model, "clientB@openkat.nl", "ClientBClientB123!!", "Client B name", "default_client_b"
    )


@pytest.fixture
def client_member(clientuser, organization):
    member = create_member(clientuser, organization)
    add_client_group(member)
    return member


@pytest.fixture
def client_member_b(clientuser_b, organization_b):
    member = create_member(clientuser_b, organization_b)
    add_client_group(member)
    return member


@pytest.fixture
def new_member(django_user_model, organization):
    user = create_user(django_user_model, "cl1@openkat.nl", "TestTest123!!", "New user", "default_new_user")
    member = create_member(user, organization)
    member.status = OrganizationMember.STATUSES.NEW
    member.save()
    return member


@pytest.fixture
def active_member(django_user_model, organization):
    user = create_user(django_user_model, "cl2@openkat.nl", "TestTest123!!", "Active user", "default_active_user")
    member = create_member(user, organization)
    member.status = OrganizationMember.STATUSES.ACTIVE
    member.save()
    return member


@pytest.fixture
def blocked_member(django_user_model, organization):
    user = create_user(django_user_model, "cl3@openkat.nl", "TestTest123!!", "Blocked user", "default_blocked_user")
    member = create_member(user, organization)
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
