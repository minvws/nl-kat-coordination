import binascii
import json
import logging
from datetime import datetime, timezone
from os import urandom
from pathlib import Path
from unittest.mock import patch

import pytest
import structlog
from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.management.color import no_style
from django.db import connections
from django.utils.translation import activate, deactivate
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.middleware import OTPMiddleware
from pytest_django import DjangoDbBlocker

from files.models import File, GenericContent
from openkat.models import GROUP_ADMIN, GROUP_CLIENT, GROUP_REDTEAM, Indemnification, Organization, OrganizationMember
from openkat.views.health import ServiceHealth
from tasks.models import Schedule
from tasks.models import Task as TaskDB

LANG_LIST = [code for code, _ in settings.LANGUAGES]

# Quiet faker locale messages down in tests.
logging.getLogger("faker").setLevel(logging.INFO)


# Copied from https://www.structlog.org/en/stable/testing.html
@pytest.fixture
def log_output():
    return structlog.testing.LogCapture()


@pytest.fixture(autouse=True)
def fixture_configure_structlog(log_output):
    structlog.configure(processors=[log_output])


@pytest.fixture
def valid_time():
    return datetime(2010, 10, 10, 10, 10, 10, tzinfo=timezone.utc)


@pytest.fixture(params=LANG_LIST)
def current_language(request):
    return request.param


@pytest.fixture
def language(current_language):
    activate(current_language)
    yield current_language
    deactivate()


def create_user(django_user_model, email, password, name, device_name, superuser=False):
    if superuser:
        user = django_user_model.objects.create_superuser(email=email, password=password, full_name=name)
    else:
        user = django_user_model(email=email, password=password, full_name=name, is_superuser=superuser)
        user.save()

    user.is_verified = lambda: True
    device = user.staticdevice_set.create(name=device_name)
    device.token_set.create(token=binascii.hexlify(urandom(8)).decode())
    return user


def create_organization(name, organization_code):
    with patch("openkat.signals.get_or_create_default_dashboard"):
        return Organization.objects.create(name=name, code=organization_code)


def create_member(user, organization):
    Indemnification.objects.create(user=user, organization=organization)

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
    admin_permissions = list(
        Permission.objects.filter(
            codename__in=[
                "view_organization",
                "view_organizationmember",
                "add_organizationmember",
                "change_organization",
                "change_organizationmember",
                "can_delete_oois",
                "add_indemnification",
                "can_scan_organization",
            ]
        ).values_list("id", flat=True)
    )
    group.permissions.set(admin_permissions)


def add_redteam_group_permissions(member):
    group = Group.objects.get(name=GROUP_REDTEAM)
    member.groups.add(group)
    redteam_permissions = list(
        Permission.objects.filter(
            codename__in=[
                "can_scan_organization",
                "can_enable_disable_plugin",
                "can_set_clearance_level",
                "can_delete_oois",
                "can_mute_findings",
                "can_view_katalogus_settings",
                "can_set_katalogus_settings",
            ]
        ).values_list("id", flat=True)
    )
    group.permissions.set(redteam_permissions)


def add_client_group_permissions(member):
    group = Group.objects.get(name=GROUP_CLIENT)
    member.groups.add(group)
    client_permissions = [Permission.objects.get(codename="can_scan_organization").id]
    group.permissions.set(client_permissions)


@pytest.fixture(autouse=True)
def seed_groups(db):
    Group.objects.get_or_create(name=GROUP_CLIENT)
    Group.objects.get_or_create(name=GROUP_REDTEAM)
    Group.objects.get_or_create(name=GROUP_ADMIN)


@pytest.fixture
def organization():
    return create_organization("Test Organization", "org")


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
def redteam_member(redteamuser, organization):
    member = create_member(redteamuser, organization)
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
def client_member(clientuser, organization) -> OrganizationMember:
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
    return mocker.patch("katalogus.client.get_katalogus_client")


@pytest.fixture
def local_repository():
    return get_local_repository()


@pytest.fixture
def task_db(organization) -> TaskDB:
    return TaskDB.objects.create(
        organization=organization,
        type="boefje",
        data={
            "id": "1b20f85f63d54baabe9ef3f19d6e3fae",
            "boefje": {"id": "test-boefje", "name": "TestBoefje", "version": None},
            "input_ooi": "Network|testnetwork",
            "organization": organization.code,
        },
        status="completed",
    )


@pytest.fixture
def report_schedule(organization):
    return Schedule.objects.create(
        type="report",
        organization=organization,
        data={
            "type": "report",
            "organisation_id": organization.code,
            "report_recipe_id": "3fed7d00-6261-4ad1-b08f-9b91434aa41e",
        },
        enabled=True,
        schedule=None,
        deadline_at=None,
        created_at=datetime(2025, 2, 12, 16, 1, 19, 951925),
        modified_at=datetime(2025, 2, 12, 16, 1, 19, 951925),
    )


@pytest.fixture
def bytes_raw_metas():
    return [
        {
            "id": "85c01c8c-c0bf-4fe8-bda5-abdf2d03117c",
            "boefje_meta": {
                "id": "6dea9549-c05d-42c9-b55b-8ad54cb9e413",
                "started_at": "2023-11-01T15:02:46.764085+00:00",
                "ended_at": "2023-11-01T15:02:47.276154+00:00",
                "boefje": {"id": "dns-sec", "version": None},
                "input_ooi": "Hostname|internet|mispoes.nl",
                "input_ooi_data": {},
                "organization": "test",
                "environment": {},
            },
            "type": "boefje/dns-sec",
        }
    ]


@pytest.fixture
def bytes_get_raw():
    byte_string = ";; Number of trusted keys: 2\\n;; Chasing: mispoes.nl."
    " A\\n\\n\\nDNSSEC Trust tree:\\nantagonist.nl. (A)\\n|---mispoes.nl. (DNSKEY keytag: 47684 alg: 13 flags:"
    " 257)\\n    |---mispoes.nl. (DS keytag: 47684 digest type: 2)\\n        "
    "|---nl. (DNSKEY keytag: 52707 alg: 13 flags: 256)\\n            "
    "|---nl. (DNSKEY keytag: 17153 alg: 13 flags: 257)\\n            "
    "|---nl. (DS keytag: 17153 digest type: 2)\\n                "
    "|---. (DNSKEY keytag: 46780 alg: 8 flags: 256)\\n                    "
    b"|---. (DNSKEY keytag: 20326 alg: 8 flags: 257)\\n;; Chase successful\\n"

    return byte_string.encode()


def setup_request(request, user):
    request = SessionMiddleware(lambda r: r)(request)
    request.session[DEVICE_ID_SESSION_KEY] = user.staticdevice_set.get().persistent_id
    request = OTPMiddleware(lambda r: r)(request)
    request = MessageMiddleware(lambda r: r)(request)

    request.user = user

    return request


@pytest.fixture
def mock_scheduler(mocker):
    return mocker.patch("openkat.views.scheduler.scheduler_client")()


def get_stub_path(file_name: str) -> Path:
    return Path(__file__).parent / "stubs" / file_name


def get_boefjes_data() -> list[dict]:
    return json.loads(get_stub_path("katalogus_boefjes.json").read_text())


@pytest.fixture
def health():
    ServiceHealth(
        service="openkat",
        healthy=True,
        version="0.0.1.dev1",
        additional=None,
        results=[
            ServiceHealth(
                service="xtdb",
                healthy=True,
                version="1.24.1",
                additional={
                    "version": "1.24.1",
                    "revision": "1164f9a3c7e36edbc026867945765fd4366c1731",
                    "indexVersion": 22,
                    "consumerState": None,
                    "kvStore": "xtdb.rocksdb.RocksKv",
                    "estimateNumKeys": 24552,
                    "size": 24053091,
                },
                results=[],
            )
        ],
    )


@pytest.fixture
def drf_admin_client(create_drf_client, admin_user):
    client = create_drf_client(admin_user)
    # We need to set this so that the test client doesn't throw an
    # exception, but will return error in the API we can test
    client.raise_request_exception = False
    return client


@pytest.fixture
def drf_redteam_client(create_drf_client, redteamuser):
    client = create_drf_client(redteamuser)
    # We need to set this so that the test client doesn't throw an
    # exception, but will return error in the API we can test
    client.raise_request_exception = False
    return client


@pytest.fixture(scope='session')
def django_xtdb_setup(request: pytest.FixtureRequest, django_db_blocker: DjangoDbBlocker):
    """
    Make sure openkat-test-api and openkat_integration in .ci/docker-compose.yml use the same database:
    Since openkat_integration calls pytest, it creates a test database by default within ci_postgres, where the
    openkat-test-api will use the regular database. This will result in the API not knowing about plugins, users or
    Authtokens created during the test, but we need this since plugins created during the test have openkat-test-api
    as a callback service.
    """
    settings.DATABASES["xtdb"]["TEST"] = {"MIRROR": "xtdb"}

    django_db_blocker.unblock()
    oois = apps.get_app_config("oois")
    ooi_models = list(oois.get_models())
    for ooi in ooi_models:
        ooi._meta.db_table = f"test_{ooi._meta.db_table}"

    yield

    con = connections["xtdb"]
    con.connect()

    flush = con.ops.sql_flush(no_style(), [ooi._meta.db_table for ooi in ooi_models])

    con.ops.execute_sql_flush(flush)


@pytest.fixture
def raw_a(client_member, client_member_b, findings_report_bytes_data):
    a, b = findings_report_bytes_data
    return File.objects.create(file=GenericContent(json.dumps(a)))


@pytest.fixture
def raw_b(client_member, client_member_b, findings_report_bytes_data):
    a, b = findings_report_bytes_data
    return File.objects.create(file=GenericContent(json.dumps(b)))


def get_dummy_data(filename: str) -> bytes:
    path = settings.BASE_DIR / "tests" / "stub_data" / filename
    return path.read_bytes()
