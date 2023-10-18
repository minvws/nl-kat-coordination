import binascii
import json
import logging
from os import urandom
from pathlib import Path
from typing import Dict
from unittest.mock import MagicMock, patch

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.utils.translation import activate, deactivate
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.middleware import OTPMiddleware
from katalogus.client import parse_plugin
from tools.models import (
    GROUP_ADMIN,
    GROUP_CLIENT,
    GROUP_REDTEAM,
    Indemnification,
    Organization,
    OrganizationMember,
)

from octopoes.models import DeclaredScanProfile, Reference, ScanLevel
from octopoes.models.ooi.findings import Finding, KATFindingType, RiskLevelSeverity
from octopoes.models.ooi.network import Network
from rocky.scheduler import Task

LANG_LIST = [code for code, _ in settings.LANGUAGES]

# Quiet faker locale messages down in tests.
logging.getLogger("faker").setLevel(logging.INFO)


@pytest.fixture(params=LANG_LIST)
def current_language(request):
    return request.param


@pytest.fixture
def language(current_language):
    activate(current_language)
    yield current_language
    deactivate()


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
        blocked=False,
        trusted_clearance_level=4,
        acknowledged_clearance_level=4,
        onboarded=False,
    )


def add_admin_group_permissions(member):
    group = Group.objects.get(name=GROUP_ADMIN)
    member.groups.add(group)
    admin_permissions = [
        Permission.objects.get(codename="view_organization").id,
        Permission.objects.get(codename="view_organizationmember").id,
        Permission.objects.get(codename="add_organizationmember").id,
        Permission.objects.get(codename="change_organization").id,
        Permission.objects.get(codename="change_organizationmember").id,
        Permission.objects.get(codename="can_delete_oois").id,
        Permission.objects.get(codename="add_indemnification").id,
        Permission.objects.get(codename="can_scan_organization").id,
    ]
    group.permissions.set(admin_permissions)


def add_redteam_group_permissions(member):
    group = Group.objects.get(name=GROUP_REDTEAM)
    member.groups.add(group)
    redteam_permissions = [
        Permission.objects.get(codename="can_scan_organization").id,
        Permission.objects.get(codename="can_enable_disable_boefje").id,
        Permission.objects.get(codename="can_set_clearance_level").id,
        Permission.objects.get(codename="can_delete_oois").id,
        Permission.objects.get(codename="can_mute_findings").id,
        Permission.objects.get(codename="can_view_katalogus_settings").id,
        Permission.objects.get(codename="can_set_katalogus_settings").id,
    ]
    group.permissions.set(redteam_permissions)


def add_client_group_permissions(member):
    group = Group.objects.get(name=GROUP_CLIENT)
    member.groups.add(group)
    client_permissions = [
        Permission.objects.get(codename="can_scan_organization").id,
    ]
    group.permissions.set(client_permissions)


@pytest.fixture(autouse=True)
def seed_groups(db):
    Group.objects.get_or_create(name=GROUP_CLIENT)
    Group.objects.get_or_create(name=GROUP_REDTEAM)
    Group.objects.get_or_create(name=GROUP_ADMIN)


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
    adminuser.user_permissions.add(Permission.objects.get(codename="view_organization"))
    add_admin_group_permissions(member)
    return member


@pytest.fixture
def admin_member_b(adminuser_b, organization_b):
    member = create_member(adminuser_b, organization_b)
    adminuser_b.user_permissions.add(Permission.objects.get(codename="view_organization"))
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
    add_client_group_permissions(member)
    return member


@pytest.fixture
def client_member_b(clientuser_b, organization_b):
    member = create_member(clientuser_b, organization_b)
    add_client_group_permissions(member)
    return member


@pytest.fixture
def client_user_two_organizations(clientuser, organization, organization_b):
    member = create_member(clientuser, organization)
    add_client_group_permissions(member)
    member = create_member(clientuser, organization_b)
    add_client_group_permissions(member)
    return clientuser


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
    member.status = OrganizationMember.STATUSES.ACTIVE
    member.blocked = True
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
def task() -> Task:
    return Task.parse_obj(
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
                    "input_ooi": "Hostname|internet|mispo.es",
                    "organization": "_dev",
                },
            },
            "status": "completed",
            "created_at": "2022-08-09 11:53:41.378292",
            "modified_at": "2022-08-09 11:54:21.002838",
        }
    )


@pytest.fixture
def lazy_task_list_with_boefje(task) -> MagicMock:
    mock = MagicMock()
    mock.__getitem__.return_value = [task]
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
def finding_types():
    return [
        KATFindingType(
            id="KAT-0001",
            description="Fake description...",
            recommendation="Fake recommendation...",
            risk_score=9.5,
            risk_severity=RiskLevelSeverity.CRITICAL,
        ),
        KATFindingType(
            id="KAT-0002",
            description="Fake description...",
            recommendation="Fake recommendation...",
            risk_score=9.5,
            risk_severity=RiskLevelSeverity.CRITICAL,
        ),
        KATFindingType(
            id="KAT-0003",
            description="Fake description...",
            recommendation="Fake recommendation...",
            risk_score=3.9,
            risk_severity=RiskLevelSeverity.LOW,
        ),
    ]


@pytest.fixture
def plugin_details():
    return parse_plugin(
        {
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
    )


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
            },
            "TEST_PROPERTY2": {
                "title": "TEST_PROPERTY2",
                "type": "integer",
                "minimum": 2,
                "maximum": 200,
                "description": "Test description2",
            },
        },
        "required": ["TEST_PROPERTY"],
    }


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


def get_stub_path(file_name: str) -> Path:
    return Path(__file__).parent / "stubs" / file_name


def get_boefjes_data() -> Dict:
    return json.loads(get_stub_path("katalogus_boefjes.json").read_text())


def get_normalizers_data() -> Dict:
    return json.loads(get_stub_path("katalogus_normalizers.json").read_text())


def get_plugins_data() -> Dict:
    return get_boefjes_data() + get_normalizers_data()


@pytest.fixture()
def mock_mixins_katalogus(mocker):
    return mocker.patch("katalogus.views.mixins.get_katalogus")


@pytest.fixture
def mock_scheduler_client_task_list(mocker):
    mock_scheduler_client_session = mocker.patch("rocky.scheduler.client.session")
    scheduler_return_value = mocker.MagicMock()
    scheduler_return_value.text = json.dumps(
        {
            "count": 1,
            "next": "http://scheduler:8000/tasks?scheduler_id=boefje-test&type=boefje&plugin_id=test_plugin&limit=10&offset=10",
            "previous": None,
            "results": [
                {
                    "id": "2e757dd3-66c7-46b8-9987-7cd18252cc6d",
                    "scheduler_id": "boefje-test",
                    "type": "boefje",
                    "p_item": {
                        "id": "2e757dd3-66c7-46b8-9987-7cd18252cc6d",
                        "scheduler_id": "boefje-test",
                        "hash": "416aa907e0b2a16c1b324f7d3261c5a4",
                        "priority": 631,
                        "data": {
                            "id": "2e757dd366c746b899877cd18252cc6d",
                            "boefje": {"id": "test-plugin", "version": None},
                            "input_ooi": "Hostname|internet|example.com",
                            "organization": "test",
                            "dispatches": [],
                        },
                        "created_at": "2023-05-09T09:37:20.899668+00:00",
                        "modified_at": "2023-05-09T09:37:20.899675+00:00",
                    },
                    "status": "completed",
                    "created_at": "2023-05-09T09:37:20.909069+00:00",
                    "modified_at": "2023-05-09T09:37:20.909071+00:00",
                }
            ],
        }
    )

    mock_scheduler_client_session.get.return_value = scheduler_return_value

    return mock_scheduler_client_session
