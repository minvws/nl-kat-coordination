import binascii
import json
import logging
from datetime import datetime, timezone
from ipaddress import IPv4Address, IPv6Address
from os import urandom
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
import structlog
from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.utils.translation import activate, deactivate
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.middleware import OTPMiddleware
from httpx import Response
from katalogus.client import Boefje, parse_plugin
from tools.enums import SCAN_LEVEL
from tools.models import GROUP_ADMIN, GROUP_CLIENT, GROUP_REDTEAM, Indemnification, Organization, OrganizationMember

from octopoes.config.settings import (
    DEFAULT_LIMIT,
    DEFAULT_OFFSET,
    DEFAULT_SCAN_LEVEL_FILTER,
    DEFAULT_SCAN_PROFILE_TYPE_FILTER,
)
from octopoes.models import OOI, DeclaredScanProfile, EmptyScanProfile, Reference, ScanLevel, ScanProfileType
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.findings import CVEFindingType, Finding, KATFindingType, RiskLevelSeverity
from octopoes.models.ooi.network import IPAddressV4, IPAddressV6, IPPort, Network, Protocol
from octopoes.models.ooi.reports import Report
from octopoes.models.ooi.service import IPService, Service
from octopoes.models.ooi.software import Software
from octopoes.models.ooi.web import URL, SecurityTXT, Website
from octopoes.models.origin import Origin, OriginType
from octopoes.models.pagination import Paginated
from octopoes.models.transaction import TransactionRecord
from octopoes.models.tree import ReferenceTree
from octopoes.models.types import OOIType
from rocky.health import ServiceHealth
from rocky.scheduler import PaginatedTasksResponse, Task

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
    return datetime.now(timezone.utc)


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
        django_user_model,
        "superuser@openkat.nl",
        "SuperSuper123!!",
        "Superuser name",
        "default",
        superuser=True,
    )


@pytest.fixture
def superuser_b(django_user_model):
    return create_user(
        django_user_model,
        "superuserB@openkat.nl",
        "SuperBSuperB123!!",
        "Superuser B name",
        "default_b",
        superuser=True,
    )


@pytest.fixture
def superuser_member(superuser, organization):
    return create_member(superuser, organization)


@pytest.fixture
def superuser_member_b(superuser_b, organization_b):
    return create_member(superuser_b, organization_b)


@pytest.fixture
def adminuser(django_user_model):
    return create_user(
        django_user_model,
        "admin@openkat.nl",
        "AdminAdmin123!!",
        "Admin name",
        "default_admin",
    )


@pytest.fixture
def adminuser_b(django_user_model):
    return create_user(
        django_user_model,
        "adminB@openkat.nl",
        "AdminBAdminB123!!",
        "Admin B name",
        "default_admin_b",
    )


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
        django_user_model,
        "redteamer@openkat.nl",
        "RedteamRedteam123!!",
        "Redteam name",
        "default_redteam",
    )


@pytest.fixture
def redteamuser_b(django_user_model):
    return create_user(
        django_user_model,
        "redteamerB@openkat.nl",
        "RedteamBRedteamB123!!",
        "Redteam B name",
        "default_redteam_b",
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
    return create_user(
        django_user_model,
        "client@openkat.nl",
        "ClientClient123!!",
        "Client name",
        "default_client",
    )


@pytest.fixture
def clientuser_b(django_user_model):
    return create_user(
        django_user_model,
        "clientB@openkat.nl",
        "ClientBClientB123!!",
        "Client B name",
        "default_client_b",
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
    user = create_user(
        django_user_model,
        "cl1@openkat.nl",
        "TestTest123!!",
        "New user",
        "default_new_user",
    )
    member = create_member(user, organization)
    member.status = OrganizationMember.STATUSES.NEW
    member.save()
    return member


@pytest.fixture
def active_member(django_user_model, organization):
    user = create_user(
        django_user_model,
        "cl2@openkat.nl",
        "TestTest123!!",
        "Active user",
        "default_active_user",
    )
    member = create_member(user, organization)
    member.status = OrganizationMember.STATUSES.ACTIVE
    member.save()
    return member


@pytest.fixture
def blocked_member(django_user_model, organization):
    user = create_user(
        django_user_model,
        "cl3@openkat.nl",
        "TestTest123!!",
        "Blocked user",
        "default_blocked_user",
    )
    member = create_member(user, organization)
    member.status = OrganizationMember.STATUSES.ACTIVE
    member.blocked = True
    member.save()
    return member


@pytest.fixture
def mock_models_katalogus(mocker):
    return mocker.patch("tools.models.get_katalogus")


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
    return Task.model_validate(
        {
            "id": "1b20f85f-63d5-4baa-be9e-f3f19d6e3fae",
            "hash": "19ed51514b37d42f79c5e95469956b05",
            "scheduler_id": "boefje-test",
            "schedule_id": None,
            "type": "boefje",
            "priority": 1,
            "data": {
                "id": "1b20f85f63d54baabe9ef3f19d6e3fae",
                "boefje": {
                    "id": "test-boefje",
                    "name": "TestBoefje",
                    "description": "Fetch the DNS record(s) of a hostname",
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
                "organization": "test",
            },
            "status": "completed",
            "created_at": "2022-08-09 11:53:41.378292",
            "modified_at": "2022-08-09 11:54:21.002838",
        }
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
                "arguments": {},
                "organization": "test",
                "runnable_hash": "ed871e9731f3d528ea92ca23c8eb18f38ac47e6d89a634b654a073fc2ca5fb50",
                "environment": {},
            },
            "mime_types": [
                {"value": "boefje/dns-sec"},
                {"value": "boefje/dns-sec-c90404f60aeacf9b254abbd250bd3214e3b1a65b5a883dcbc"},
                {"value": "dns-sec"},
            ],
            "secure_hash": "sha512:23e40f3e0c4381b89a296a5708a3c7a2dff369dc272b5cbce584d0fd7e17b1a5ebb1a947"
            "be36ed19e8930116a46be2f4b450353b786696f83c328f197a8ae741",
            "signing_provider_url": None,
            "hash_retrieval_link": "a9b261d1-e981-42db-bd92-ee0c36372678",
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


@pytest.fixture
def lazy_task_list_with_boefje(task) -> MagicMock:
    mock = MagicMock()
    mock.__getitem__.return_value = [task]
    mock.count.return_value = 1
    return mock


@pytest.fixture
def network() -> Network:
    return Network(
        name="testnetwork",
        scan_profile=DeclaredScanProfile(reference=Reference.from_str("Network|testnetwork"), level=ScanLevel.L1),
    )


@pytest.fixture
def url(network) -> URL:
    return URL(
        scan_profile=DeclaredScanProfile(
            scan_profile_type="declared",
            reference=Reference("URL|testnetwork|http://example.com/"),
            level=ScanLevel.L1,
        ),
        user_id=None,
        primary_key="URL|testnetwork|http://example.com/",
        network=network.reference,
        raw="http://example.com",
        web_url=Reference("HostnameHTTPURL|http|testnetwork|example.com|80|/"),
    )


@pytest.fixture
def ipaddressv4(network) -> IPAddressV4:
    return IPAddressV4(network=network.reference, address=IPv4Address("192.0.2.1"))


@pytest.fixture
def ipaddressv6(network) -> IPAddressV6:
    return IPAddressV6(network=network.reference, address=IPv6Address("2001:db8::1"))


@pytest.fixture
def ip_port(ipaddressv4) -> IPPort:
    return IPPort(address=ipaddressv4.reference, port=80, protocol=Protocol.TCP)


@pytest.fixture
def ip_port_443(ipaddressv4) -> IPPort:
    return IPPort(address=ipaddressv4.reference, port=443, protocol=Protocol.TCP)


@pytest.fixture
def hostname(network) -> Hostname:
    return Hostname(name="example.com", network=network.reference)


@pytest.fixture
def website(ip_service: IPService, hostname: Hostname):
    return Website(
        ip_service=ip_service.reference,
        hostname=hostname.reference,
    )


@pytest.fixture
def security_txt(website: Website, url: URL):
    return SecurityTXT(website=website.reference, url=url.reference, security_txt="example")


@pytest.fixture
def service() -> Service:
    return Service(name="domain")


@pytest.fixture
def ip_service(ip_port: IPPort, service: Service):
    return IPService(ip_port=ip_port.reference, service=service.reference)


@pytest.fixture
def software() -> Software:
    return Software(name="DICOM")


@pytest.fixture
def cve_finding_type_2023_38408() -> CVEFindingType:
    return CVEFindingType(
        id="CVE-2023-38408",
        description="The PKCS#11 feature in ssh-agent in OpenSSH before 9.3p2 has an insufficiently "
        "trustworthy search path, leading to remote code execution if an agent is forwarded to an "
        "attacker-controlled system. ",
        source="https://cve.circl.lu/cve/CVE-2023-38408",
        risk_score=9.8,
        risk_severity=RiskLevelSeverity.CRITICAL,
    )


@pytest.fixture
def cve_finding_type_2019_8331() -> CVEFindingType:
    return CVEFindingType(
        id="CVE-2019-8331",
        description="In Bootstrap before 3.4.1 and 4.3.x before 4.3.1, XSS is possible in the tooltip or "
        "popover data-template attribute.",
        source="https://cve.circl.lu/cve/CVE-2019-8331",
        risk_score=6.1,
        risk_severity=RiskLevelSeverity.MEDIUM,
    )


@pytest.fixture
def cve_finding_type_2019_2019() -> CVEFindingType:
    return CVEFindingType(
        id="CVE-2019-2019",
        description="In ce_t4t_data_cback of ce_t4t.cc, there is a possible out-of-bound read due to a missing bounds "
        "check. This could lead to local information disclosure with no additional execution privileges "
        "needed. User interaction is needed for exploitation.Product: AndroidVersions: Android-7.0 "
        "Android-7.1.1 Android-7.1.2 Android-8.0 Android-8.1 Android-9Android ID: A-115635871",
        source="https://cve.circl.lu/cve/CVE-2019-2019",
        risk_score=6.5,
        risk_severity=RiskLevelSeverity.MEDIUM,
    )


@pytest.fixture
def cve_finding_2023_38408() -> Finding:
    return Finding(
        finding_type=Reference.from_str("CVEFindingType|CVE-2023-38408"),
        ooi=Reference.from_str(
            "Finding|SoftwareInstance|HostnameHTTPURL|https|internet|mispo.es|443|/|Software|Bootstrap|3.3.7|cpe:/a:getbootstrap:bootstrap|CVE-2023-38408"
        ),
        proof=None,
        description="Vulnerability CVE-2023-38408 detected",
        reproduce=None,
    )


@pytest.fixture
def cve_finding_2019_8331() -> Finding:
    return Finding(
        finding_type=Reference.from_str("CVEFindingType|CVE-2019-8331"),
        ooi=Reference.from_str(
            "Finding|SoftwareInstance|HostnameHTTPURL|https|internet|mispo.es|443|/|Software|Bootstrap|3.3.7|cpe:/a:getbootstrap:bootstrap|CVE-2019-8331"
        ),
        proof=None,
        description="Vulnerability CVE-2019-8331 detected",
        reproduce=None,
    )


@pytest.fixture
def cve_finding_2019_2019() -> Finding:
    return Finding(
        finding_type=Reference.from_str("CVEFindingType|CVE-2019-2019"),
        ooi=Reference.from_str(
            "Finding|SoftwareInstance|HostnameHTTPURL|https|internet|mispo.es|443|/|Software|Bootstrap|3.3.7|cpe:/a:getbootstrap:bootstrap|CVE-2019-2019"
        ),
        proof=None,
        description="Vulnerability CVE-2019-2019 detected",
        reproduce=None,
    )


@pytest.fixture
def cve_finding_type_no_score() -> CVEFindingType:
    return CVEFindingType(
        id="CVE-0000-0001",
        description="CVE Finding without score",
        source="https://cve.circl.lu/cve/CVE-0000-0001",
        risk_severity=RiskLevelSeverity.UNKNOWN,
    )


@pytest.fixture
def cve_finding_no_score() -> Finding:
    return Finding(
        finding_type=Reference.from_str("CVEFindingType|CVE-0000-0001"),
        ooi=Reference.from_str(
            "Finding|SoftwareInstance|HostnameHTTPURL|https|internet|mispo.es|443|/|Software|Bootstrap|3.3.7|cpe:/a:getbootstrap:bootstrap|CVE-0000-0001"
        ),
        proof=None,
        description="Vulnerability CVE-0000-0001 detected",
        reproduce=None,
    )


@pytest.fixture
def finding() -> Finding:
    return Finding(
        finding_type=Reference.from_str("KATFindingType|KAT-0001"),
        ooi=Reference.from_str("Network|testnetwork"),
        proof="proof",
        description="description",
        reproduce="reproduce",
    )


@pytest.fixture
def web_report_finding_types():
    return [
        KATFindingType(id="KAT-NO-CSP"),
        KATFindingType(id="KAT-CSP-VULNERABILITIES"),
        KATFindingType(id="KAT-NO-HTTPS-REDIRECT"),
        KATFindingType(id="KAT-NO-CERTIFICATE"),
        KATFindingType(id="KAT-NO-SECURITY-TXT"),
        KATFindingType(id="KAT-UNCOMMON-OPEN-PORT"),
        KATFindingType(id="KAT-OPEN-SYSADMIN-PORT"),
        KATFindingType(id="KAT-OPEN-DATABASE-PORT"),
        KATFindingType(id="KAT-CERTIFICATE-EXPIRED"),
        KATFindingType(id="KAT-CERTIFICATE-EXPIRING-SOON"),
    ]


@pytest.fixture
def no_rpki_finding_type() -> KATFindingType:
    return KATFindingType(id="KAT-NO-RPKI")


@pytest.fixture
def invalid_rpki_finding_type() -> KATFindingType:
    return KATFindingType(id="KAT-INVALID-RPKI")


@pytest.fixture
def finding_types() -> list[KATFindingType]:
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
def tree_data_no_findings():
    return {
        "root": {
            "reference": "Finding|Network|testnetwork|KAT-0001",
            "children": {"ooi": [{"reference": "Network|testnetwork", "children": {}}]},
        },
        "store": {},
    }


@pytest.fixture
def tree_data_findings():
    return {
        "root": {
            "reference": "Finding|Network|testnetwork|KAT-0001",
            "children": {"ooi": [{"reference": "Network|testnetwork", "children": {}}]},
        },
        "store": {
            "Network|testnetwork": {
                "object_type": "Network",
                "primary_key": "Network|testnetwork",
                "name": "testnetwork",
            },
            "Finding|Network|testnetwork|KAT-0001": {
                "object_type": "Finding",
                "primary_key": "Finding|Network|testnetwork|KAT-0001",
                "ooi": "Network|testnetwork",
                "finding_type": "KATFindingType|KAT-0001",
            },
            "Finding|Network|testnetwork|KAT-0002": {
                "object_type": "Finding",
                "primary_key": "Finding|Network|testnetwork|KAT-0002",
                "ooi": "Network|testnetwork",
                "finding_type": "KATFindingType|KAT-0002",
            },
            "Finding|Network|testnetwork|KAT-0003": {
                "object_type": "Finding",
                "primary_key": "Finding|Network|testnetwork|KAT-0003",
                "ooi": "Network|testnetwork",
                "finding_type": "KATFindingType|KAT-0001",
            },
        },
    }


@pytest.fixture
def tree_data_dns_findings():
    return {
        "root": {
            "reference": "Finding|Network|testnetwork|KAT-0001",
            "children": {"ooi": [{"reference": "Network|testnetwork", "children": {}}]},
        },
        "store": {
            "Finding|Network|testnetwork|KAT-0001": {
                "object_type": "Finding",
                "primary_key": "Finding|Network|testnetwork|KAT-0001",
                "ooi": "Network|testnetwork",
                "finding_type": "KATFindingType|KAT-NO-CAA",
            },
            "Finding|Network|testnetwork|KAT-0002": {
                "object_type": "Finding",
                "primary_key": "Finding|Network|testnetwork|KAT-0002",
                "ooi": "Network|testnetwork",
                "finding_type": "KATFindingType|KAT-NO-DKIM",
            },
            "Finding|Network|testnetwork|KAT-0003": {
                "object_type": "Finding",
                "primary_key": "Finding|Network|testnetwork|KAT-0003",
                "ooi": "Network|testnetwork",
                "finding_type": "KATFindingType|KAT-NO-DMARC",
            },
            "Finding|Network|testnetwork|KAT-0004": {
                "object_type": "Finding",
                "primary_key": "Finding|Network|testnetwork|KAT-0004",
                "ooi": "Network|testnetwork",
                "finding_type": "KATFindingType|KAT-NO-DNSSEC",
            },
            "Finding|Network|testnetwork|KAT-0005": {
                "object_type": "Finding",
                "primary_key": "Finding|Network|testnetwork|KAT-0005",
                "ooi": "Network|testnetwork",
                "finding_type": "KATFindingType|KAT-NO-SPF",
            },
            "Finding|Network|testnetwork|KAT-0006": {
                "object_type": "Finding",
                "primary_key": "Finding|Network|testnetwork|KAT-0006",
                "ooi": "Network|testnetwork",
                "finding_type": "KATFindingType|KAT-INVALID-SPF",
            },
            "Finding|Network|testnetwork|KAT-0007": {
                "object_type": "Finding",
                "primary_key": "Finding|Network|testnetwork|KAT-0007",
                "ooi": "Network|testnetwork",
                "finding_type": "KATFindingType|KAT-NAMESERVER-NO-IPV6",
            },
            "Finding|Network|testnetwork|KAT-0008": {
                "object_type": "Finding",
                "primary_key": "Finding|Network|testnetwork|KAT-0008",
                "ooi": "Network|testnetwork",
                "finding_type": "KATFindingType|KAT-NAMESERVER-NO-TWO-IPV6",
            },
            "DNSSOARecord|Network|testnetwork|KAT-0009": {
                "object_type": "DNSSOARecord",
                "primary_key": "DNSSOARecord|Network|testnetwork|KAT-0009",
                "hostname": "Hostname|internet|example.com",
                "dns_record_type": "SOA",
                "value": "fake value",
                "ttl": 3600,
                "soa_hostname": "Hostname|internet|example.com",
            },
            "DNSARecord|Network|testnetwork|KAT-00010": {
                "object_type": "DNSARecord",
                "primary_key": "DNSARecord|Network|testnetwork|KAT-00010",
                "hostname": "Hostname|internet|example.com",
                "dns_record_type": "A",
                "value": "fake value",
                "address": "IPAddressV4|internet|127.0.0.1",
            },
        },
    }


@pytest.fixture
def finding_type_kat_no_caa() -> KATFindingType:
    return KATFindingType(
        id="KAT-NO-CAA",
        description="Fake description...",
        recommendation="Fake recommendation...",
        risk_score=9.5,
        risk_severity=RiskLevelSeverity.CRITICAL,
    )


@pytest.fixture
def finding_type_kat_invalid_spf() -> KATFindingType:
    return KATFindingType(
        id="KAT-INVALID-SPF",
        description="Fake description...",
        recommendation="Fake recommendation...",
        risk_score=6.0,
        risk_severity=RiskLevelSeverity.MEDIUM,
    )


@pytest.fixture
def finding_type_kat_nameserver_no_ipv6() -> KATFindingType:
    return KATFindingType(
        id="KAT-NAMESERVER-NO-IPV6",
        description="Fake description...",
        recommendation="Fake recommendation...",
        risk_score=9.5,
        risk_severity=RiskLevelSeverity.CRITICAL,
    )


@pytest.fixture
def finding_type_kat_no_two_ipv6() -> KATFindingType:
    return KATFindingType(
        id="KAT-NAMESERVER-NO-TWO-IPV6",
        description="Fake description...",
        recommendation="Fake recommendation...",
        risk_score=1.0,
        risk_severity=RiskLevelSeverity.LOW,
    )


@pytest.fixture
def cipher_finding_types() -> list[KATFindingType]:
    return [
        KATFindingType(
            id="KAT-RECOMMENDATION-BAD-CIPHER",
            description="Fake description...",
            recommendation="Fake recommendation...",
            risk_score=3.0,
            risk_severity=RiskLevelSeverity.RECOMMENDATION,
        ),
        KATFindingType(
            id="KAT-CRITICAL-BAD-CIPHER",
            description="Fake description...",
            recommendation="Fake recommendation...",
            risk_score=10.0,
            risk_severity=RiskLevelSeverity.CRITICAL,
        ),
    ]


@pytest.fixture
def cipher_finding_type() -> KATFindingType:
    return KATFindingType(
        id="KAT-MEDIUM-BAD-CIPHER",
        description="Fake description...",
        recommendation="Fake recommendation...",
        risk_score=6.0,
        risk_severity=RiskLevelSeverity.MEDIUM,
    )


@pytest.fixture
def finding_type_kat_no_spf() -> KATFindingType:
    return KATFindingType(
        id="KAT-NO-SPF",
        description="Fake description...",
        recommendation="Fake recommendation...",
        risk_score=9.5,
        risk_severity=RiskLevelSeverity.CRITICAL,
    )


@pytest.fixture
def finding_type_kat_no_dmarc() -> KATFindingType:
    return KATFindingType(
        id="KAT-NO-DMARC",
        description="Fake description...",
        recommendation="Fake recommendation...",
        risk_score=9.5,
        risk_severity=RiskLevelSeverity.CRITICAL,
    )


@pytest.fixture
def finding_type_kat_no_dkim() -> KATFindingType:
    return KATFindingType(
        id="KAT-NO-DKIM",
        description="Fake description...",
        recommendation="Fake recommendation...",
        risk_score=9.5,
        risk_severity=RiskLevelSeverity.CRITICAL,
    )


@pytest.fixture
def finding_type_kat_uncommon_open_port() -> KATFindingType:
    return KATFindingType(
        id="KAT-UNCOMMON-OPEN-PORT",
        description="Fake description...",
        recommendation="Fake recommendation...",
        risk_score=9.5,
        risk_severity=RiskLevelSeverity.CRITICAL,
    )


@pytest.fixture
def finding_type_kat_open_sysadmin_port() -> KATFindingType:
    return KATFindingType(
        id="KAT-OPEN-SYSADMIN-PORT",
        description="Fake description...",
        recommendation="Fake recommendation...",
        risk_score=8.5,
        risk_severity=RiskLevelSeverity.HIGH,
    )


@pytest.fixture
def finding_type_kat_open_database_port() -> KATFindingType:
    return KATFindingType(
        id="KAT-OPEN-DATABASE-PORT",
        description="Fake description...",
        recommendation="Fake recommendation...",
        risk_score=6.5,
        risk_severity=RiskLevelSeverity.MEDIUM,
    )


@pytest.fixture
def finding_type_kat_no_dnssec() -> KATFindingType:
    return KATFindingType(
        id="KAT-NO-DNSSEC",
        description="Fake description...",
        recommendation="Fake recommendation...",
        risk_severity=RiskLevelSeverity.PENDING,
    )


@pytest.fixture
def finding_type_kat_invalid_dnssec() -> KATFindingType:
    return KATFindingType(
        id="KAT-INVALID-DNSSEC",
        recommendation="Fake recommendation...",
        risk_score=3.0,
        risk_severity=RiskLevelSeverity.LOW,
    )


@pytest.fixture
def tree_data_tls_findings_and_suites():
    return {
        "root": {
            "reference": "",
            "children": {"ooi": [{"reference": "", "children": {}}]},
        },
        "store": {
            "Finding|Network|testnetwork|KAT-0001": {
                "object_type": "Finding",
                "primary_key": "Finding|Network|testnetwork|KAT-0001",
                "ooi": "Network|testnetwork",
                "description": "Fake description with cipher_suite_name ECDHE-RSA-AES128-SHA",
                "finding_type": "KATFindingType|KAT-RECOMMENDATION-BAD-CIPHER",
            },
            "Finding|Network|testnetwork|KAT-0002": {
                "object_type": "Finding",
                "primary_key": "Finding|Network|testnetwork|KAT-0002",
                "ooi": "Network|testnetwork",
                "description": "Fake description with cipher_suite_name ECDHE-RSA-AES256-SHA",
                "finding_type": "KATFindingType|KAT-MEDIUM-BAD-CIPHER",
            },
            "Finding|Network|testnetwork|KAT-0003": {
                "object_type": "Finding",
                "primary_key": "Finding|Network|testnetwork|KAT-0003",
                "ooi": "Network|testnetwork",
                "description": "Fake description...",
                "finding_type": "KATFindingType|KAT-CRITICAL-BAD-CIPHER",
            },
            "TLSCipher|Network|testnetwork|KAT-0004": {
                "object_type": "TLSCipher",
                "primary_key": "TLSCipher|Network|testnetwork|KAT-0004|tcp|443|https",
                "ip_service": "IPService",
                "ooi": "Network|testnetwork",
                "suites": {
                    "TLSv1": [
                        {
                            "cipher_suite_alias": "TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA",
                            "encryption_algorithm": "AES",
                            "cipher_suite_name": "ECDHE-RSA-AES128-SHA",
                            "bits": 128,
                            "key_size": 256,
                            "key_exchange_algorithm": "ECDH",
                            "cipher_suite_code": "xc013",
                        },
                        {
                            "cipher_suite_alias": "TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA",
                            "encryption_algorithm": "AES",
                            "cipher_suite_name": "ECDHE-RSA-AES256-SHA",
                            "bits": 256,
                            "key_size": 256,
                            "key_exchange_algorithm": "ECDH",
                            "cipher_suite_code": "xc014",
                        },
                    ],
                },
            },
        },
    }


@pytest.fixture
def plugin_details():
    return parse_plugin(
        {
            "id": "test-boefje",
            "type": "boefje",
            "name": "TestBoefje",
            "created": "2023-05-09T09:37:20.909069+00:00",
            "description": "Meows to the moon",
            "scan_level": 1,
            "consumes": ["Network"],
            "produces": ["Network"],
            "enabled": True,
            "boefje_schema": {},
            "oci_image": None,
            "oci_arguments": ["-test", "-arg"],
        }
    )


@pytest.fixture
def plugin_details_with_container():
    return parse_plugin(
        {
            "id": "test-boefje",
            "type": "boefje",
            "name": "TestBoefje",
            "created": "2023-05-09T09:37:20.909069+00:00",
            "description": "Meows to the moon",
            "scan_level": 1,
            "consumes": ["Network"],
            "produces": ["Network"],
            "enabled": True,
            "boefje_schema": {},
            "oci_image": "ghcr.io/test/image:123",
            "oci_arguments": ["-test", "-arg"],
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


@pytest.fixture
def plugin_schema_no_required():
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
    }


parent_report = [
    Report(
        object_type="Report",
        scan_profile=None,
        user_id=None,
        primary_key="Report|e821aaeb-a6bd-427f-b064-e46837911a5d",
        name="Test Parent Report",
        report_type="concatenated-report",
        template="report.html",
        date_generated=datetime(2024, 1, 1, 23, 59, 59, 999999),
        input_oois=[],
        report_id=UUID("e821aaeb-a6bd-427f-b064-e46837911a5d"),
        organization_code="test_organization",
        organization_name="Test Organization",
        organization_tags=[],
        data_raw_id="a5ccf97b-d4e9-442d-85bf-84e739b6d3ed",
        observed_at=datetime(2024, 1, 1, 23, 59, 59, 999999),
        parent_report=None,
        has_parent=False,
    ),
]

subreports = [
    Report(
        object_type="Report",
        scan_profile=None,
        user_id=None,
        primary_key="Report|1730b72f-b115-412e-ad44-dae6ab3edff9",
        name="RPKI Report",
        report_type="rpki-report",
        template="rpki_report/report.html",
        date_generated=datetime(2024, 1, 1, 23, 59, 59, 999999),
        input_oois=[Reference("Hostname|internet|example.com")],
        report_id=UUID("1730b72f-b115-412e-ad44-dae6ab3edff9"),
        organization_code="test_organization",
        organization_name="Test Organization",
        organization_tags=[],
        data_raw_id="acbd2250-85f4-471a-ab70-ba1750280194",
        observed_at=datetime(2024, 1, 1, 23, 59, 59, 999999),
        parent_report=Reference("Report|e821aaeb-a6bd-427f-b064-e46837911a5d"),
        has_parent=True,
    ),
    Report(
        object_type="Report",
        scan_profile=None,
        user_id=None,
        primary_key="Report|463c7f72-fef9-42ef-baf9-f10fcfb91abe",
        name="Safe Connections Report",
        report_type="safe-connections-report",
        template="safe_connections_report/report.html",
        date_generated=datetime(2024, 1, 1, 23, 59, 59, 999999),
        input_oois=[Reference("Hostname|internet|example.com")],
        report_id=UUID("463c7f72-fef9-42ef-baf9-f10fcfb91abe"),
        organization_code="test_organization",
        organization_name="Test Organization",
        organization_tags=[],
        data_raw_id="ba2d86b8-aca8-4009-adc0-e3d59ea34904",
        observed_at=datetime(2024, 1, 1, 23, 59, 59, 999999),
        parent_report=Reference("Report|e821aaeb-a6bd-427f-b064-e46837911a5d"),
        has_parent=True,
    ),
    Report(
        object_type="Report",
        scan_profile=None,
        user_id=None,
        primary_key="Report|47a28977-04c6-43b6-9705-3c5f0c955833",
        name="System Report",
        report_type="systems-report",
        template="systems_report/report.html",
        date_generated=datetime(2024, 1, 1, 23, 59, 59, 999999),
        input_oois=[Reference("Hostname|internet|example.com")],
        report_id=UUID("47a28977-04c6-43b6-9705-3c5f0c955833"),
        organization_code="test_organization",
        organization_name="Test Organization",
        organization_tags=[],
        data_raw_id="3d2ea955-13c1-46f6-81f3-edfe72d8af0b",
        observed_at=datetime(2024, 1, 1, 23, 59, 59, 999999),
        parent_report=Reference("Report|e821aaeb-a6bd-427f-b064-e46837911a5d"),
        has_parent=True,
    ),
    Report(
        object_type="Report",
        scan_profile=None,
        user_id=None,
        primary_key="Report|57c8f1b9-da3e-48ca-acb1-554e6966b4aa",
        name="Mail Report",
        report_type="mail-report",
        template="mail_report/report.html",
        date_generated=datetime(2024, 1, 1, 23, 59, 59, 999999),
        input_oois=[Reference("Hostname|internet|example.com")],
        report_id=UUID("57c8f1b9-da3e-48ca-acb1-554e6966b4aa"),
        organization_code="test_organization",
        organization_name="Test Organization",
        organization_tags=[],
        data_raw_id="fe4d0f5d-5447-47d3-952d-74544c8a9d8d",
        observed_at=datetime(2024, 1, 1, 23, 59, 59, 999999),
        parent_report=Reference("Report|e821aaeb-a6bd-427f-b064-e46837911a5d"),
        has_parent=True,
    ),
    Report(
        object_type="Report",
        scan_profile=None,
        user_id=None,
        primary_key="Report|8075a64c-1acb-44b8-8376-b68d4ee972e5",
        name="IPv6 Report",
        report_type="ipv6-report",
        template="ipv6_report/report.html",
        date_generated=datetime(2024, 1, 1, 23, 59, 59, 999999),
        input_oois=[Reference("Hostname|internet|example.com")],
        report_id=UUID("8075a64c-1acb-44b8-8376-b68d4ee972e5"),
        organization_code="test_organization",
        organization_name="Test Organization",
        organization_tags=[],
        data_raw_id="3ca35c20-1139-4bf4-a11a-a0b83f3c48ff",
        observed_at=datetime(2024, 1, 1, 23, 59, 59, 999999),
        parent_report=Reference("Report|e821aaeb-a6bd-427f-b064-e46837911a5d"),
        has_parent=True,
    ),
    Report(
        object_type="Report",
        scan_profile=None,
        user_id=None,
        primary_key="Report|8f3c6b75-b237-4c9a-8d9b-7745f3708d4a",
        name="Web System Report",
        report_type="web-system-report",
        template="web_system_report/report.html",
        date_generated=datetime(2024, 1, 1, 23, 59, 59, 999999),
        input_oois=[Reference("Hostname|internet|example.com")],
        report_id=UUID("8f3c6b75-b237-4c9a-8d9b-7745f3708d4a"),
        organization_code="test_organization",
        organization_name="Test Organization",
        organization_tags=[],
        data_raw_id="1e419bee-672f-4561-b3b9-f47bd6ce60b7",
        observed_at=datetime(2024, 1, 1, 23, 59, 59, 999999),
        parent_report=Reference("Report|e821aaeb-a6bd-427f-b064-e46837911a5d"),
        has_parent=True,
    ),
    Report(
        object_type="Report",
        scan_profile=None,
        user_id=None,
        primary_key="Report|8f3c6b75-b237-4c9a-8d9b-7745f3708d4a",
        name="Web System Report",
        report_type="web-system-report",
        template="web_system_report/report.html",
        date_generated=datetime(2024, 1, 1, 23, 59, 59, 999999),
        input_oois=[Reference("Hostname|internet|example2.com")],
        report_id=UUID("8f3c6b75-b237-4c9a-8d9b-7745f3708d4a"),
        organization_code="test_organization",
        organization_name="Test Organization",
        organization_tags=[],
        data_raw_id="1e419bee-672f-4561-b3b9-f47bd6ce60b7",
        observed_at=datetime(2024, 1, 1, 23, 59, 59, 999999),
        parent_report=Reference("Report|e821aaeb-a6bd-427f-b064-e46837911a5d"),
        has_parent=True,
    ),
]

dns_report = [
    Report(
        object_type="Report",
        scan_profile=None,
        primary_key="Report|e821aaeb-a6bd-427f-b064-e46837913b4d",
        name="DNS Report",
        report_type="dns-report",
        template="dns_report/report.html",
        date_generated=datetime(2024, 1, 1, 23, 59, 59, 999999),
        input_oois=[],
        report_id=UUID("e821aaeb-a6bd-427f-b064-e46837911a5d"),
        organization_code="test_organization",
        organization_name="Test Organization",
        organization_tags=[],
        data_raw_id="a5ccf97b-d4e9-442d-85bf-84e739b63da9s",
        observed_at=datetime(2024, 1, 1, 23, 59, 59, 999999),
        parent_report=None,
        has_parent=False,
    ),
]


@pytest.fixture
def report_list_one_subreport():
    return [
        (
            subreports[0],
            [],
        )
    ]


@pytest.fixture
def report_list_two_subreports():
    return [
        (
            parent_report[0],
            [
                subreports[5],
                subreports[6],
            ],
        )
    ]


@pytest.fixture
def report_list_six_subreports():
    return [
        (
            parent_report[0],
            [
                subreports[0],
                subreports[1],
                subreports[2],
                subreports[3],
                subreports[4],
                subreports[5],
            ],
        )
    ]


@pytest.fixture
def get_subreports() -> list[tuple[str, Report]]:
    return [
        (parent_report[0].primary_key, subreports[0]),
        (parent_report[0].primary_key, subreports[1]),
        (parent_report[0].primary_key, subreports[2]),
        (parent_report[0].primary_key, subreports[3]),
        (parent_report[0].primary_key, subreports[4]),
        (parent_report[0].primary_key, subreports[5]),
    ]


def setup_request(request, user):
    request = SessionMiddleware(lambda r: r)(request)
    request.session[DEVICE_ID_SESSION_KEY] = user.staticdevice_set.get().persistent_id
    request = OTPMiddleware(lambda r: r)(request)
    request = MessageMiddleware(lambda r: r)(request)

    request.user = user

    return request


@pytest.fixture
def mock_scheduler(mocker):
    return mocker.patch("rocky.views.scheduler.scheduler_client")()


def get_stub_path(file_name: str) -> Path:
    return Path(__file__).parent / "stubs" / file_name


def get_boefjes_data() -> list[dict]:
    return json.loads(get_stub_path("katalogus_boefjes.json").read_text())


def get_normalizers_data() -> list[dict]:
    return json.loads(get_stub_path("katalogus_normalizers.json").read_text())


def get_aggregate_report_data():
    return json.loads(get_stub_path("aggregate_report_data.json").read_text())


def get_plugins_data() -> list[dict]:
    return get_boefjes_data() + get_normalizers_data()


@pytest.fixture()
def mock_mixins_katalogus(mocker):
    return mocker.patch("katalogus.views.mixins.get_katalogus")


@pytest.fixture
def mock_scheduler_client_task_list(mock_scheduler):
    mock_scheduler_session = mock_scheduler._client
    response = Response(
        200,
        content=(
            json.dumps(
                {
                    "count": 1,
                    "next": "http://scheduler:8000/tasks?scheduler_id=boefje-test&type=boefje&plugin_id=test_plugin&limit=10&offset=10",
                    "previous": None,
                    "results": [
                        {
                            "id": "2e757dd3-66c7-46b8-9987-7cd18252cc6d",
                            "hash": "416aa907e0b2a16c1b324f7d3261c5a4",
                            "scheduler_id": "boefje-test",
                            "schedule_id": None,
                            "type": "boefje",
                            "priority": 631,
                            "data": {
                                "id": "2e757dd366c746b899877cd18252cc6d",
                                "boefje": {"id": "test-plugin", "version": None},
                                "input_ooi": "Hostname|internet|example.com",
                                "organization": "test",
                                "dispatches": [],
                            },
                            "status": "completed",
                            "created_at": "2023-05-09T09:37:20.909069+00:00",
                            "modified_at": "2023-05-09T09:37:20.909071+00:00",
                        }
                    ],
                }
            ).encode()
        ),
    )

    mock_scheduler_session.get.return_value = response

    return mock_scheduler_session


class MockOctopoesAPIConnector:
    oois: dict[Reference, OOI]
    queries: dict[str, dict[Reference | str | None, list[OOI]]]
    valid_time: datetime

    def __init__(self, valid_time: datetime):
        self.valid_time = valid_time

    def get(self, reference: Reference, valid_time: datetime | None = None) -> OOI:
        return self.oois[reference]

    def get_tree(
        self,
        reference: Reference,
        valid_time: datetime,
        types: set = frozenset(),
        depth: int = 1,
    ) -> ReferenceTree:
        return self.tree[reference]

    def query(
        self,
        path: str,
        valid_time: datetime,
        source: Reference | str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[OOI]:
        return self.queries[path][source]

    def query_many(
        self,
        path: str,
        valid_time: datetime,
        sources: list[OOI | Reference | str],
    ) -> list[tuple[str, OOIType]]:
        result = []

        for source in sources:
            for ooi in self.queries[path][str(source)]:
                result.append((str(source), ooi))

        return result

    def get_history(self, reference: Reference) -> list[TransactionRecord]:
        return [
            TransactionRecord(
                txTime=self.valid_time,
                txId=287,
                validTime=self.valid_time,
                contentHash="636a28da4792b9f5007143bb35bd37d48662df9b",
            )
        ]

    def list_origins(
        self,
        valid_time: datetime | None = None,
        source: Reference | None = None,
        result: Reference | None = None,
        task_id: UUID | None = None,
        origin_type: OriginType | None = None,
    ) -> list[Origin]:
        return []

    def list_objects(
        self,
        types: set[type[OOI]],
        valid_time: datetime,
        offset: int = DEFAULT_OFFSET,
        limit: int = DEFAULT_LIMIT,
        scan_level: set[ScanLevel] = DEFAULT_SCAN_LEVEL_FILTER,
        scan_profile_type: set[ScanProfileType] = DEFAULT_SCAN_PROFILE_TYPE_FILTER,
    ) -> Paginated[OOIType]:
        return Paginated[OOIType](items=list(self.oois.values()), count=len(self.oois))


@pytest.fixture
def mock_octopoes_api_connector(valid_time):
    return MockOctopoesAPIConnector(valid_time)


@pytest.fixture
def listed_hostnames(network) -> list[Hostname]:
    return [
        Hostname(network=network.reference, name="example.com"),
        Hostname(network=network.reference, name="a.example.com"),
        Hostname(network=network.reference, name="b.example.com"),
        Hostname(network=network.reference, name="c.example.com"),
        Hostname(network=network.reference, name="d.example.com"),
        Hostname(network=network.reference, name="e.example.com"),
        Hostname(network=network.reference, name="f.example.com"),
    ]


@pytest.fixture
def paginated_task_list(task):
    return PaginatedTasksResponse(
        count=1,
        next="",
        previous=None,
        results=[task],
    )


@pytest.fixture
def reports_more_input_oois():
    return [
        (
            Report(
                object_type="Report",
                scan_profile=None,
                primary_key="Report|e821aaeb-a6bd-427f-b064-e46837911a5d",
                name="Test Parent Report",
                report_type="concatenated-report",
                template="report.html",
                date_generated=datetime(2024, 1, 1, 23, 59, 59, 999999),
                input_oois=[],
                report_id=UUID("e821aaeb-a6bd-427f-b064-e46837911a5d"),
                organization_code="test_organization",
                organization_name="Test Organization",
                organization_tags=[],
                data_raw_id="a5ccf97b-d4e9-442d-85bf-84e739b6d3ed",
                observed_at=datetime(2024, 1, 1, 23, 59, 59, 999999),
                parent_report=None,
                has_parent=False,
            ),
            [
                Report(
                    object_type="Report",
                    scan_profile=None,
                    primary_key="Report|1730b72f-b115-412e-ad44-dae6ab3edff7",
                    name="RPKI Report",
                    report_type="rpki-report",
                    template="rpki_report/report.html",
                    date_generated=datetime(2024, 1, 1, 23, 59, 59, 999999),
                    input_oois=[
                        Reference("Hostname|internet|example1.com"),
                        Reference("Hostname|internet|example2.com"),
                    ],
                    report_id=UUID("1730b72f-b115-412e-ad44-dae6ab3edff7"),
                    organization_code="test_organization",
                    organization_name="Test Organization",
                    organization_tags=[],
                    data_raw_id="acbd2250-85f4-471a-ab70-ba1750280192",
                    observed_at=datetime(2024, 1, 1, 23, 59, 59, 999999),
                    parent_report=Reference("Report|e821aaeb-a6bd-427f-b064-e46837911a5d"),
                    has_parent=True,
                ),
                Report(
                    object_type="Report",
                    scan_profile=None,
                    primary_key="Report|1730b72f-b115-412e-ad44-dae6ab3edff9",
                    name="RPKI Report",
                    report_type="rpki-report",
                    template="rpki_report/report.html",
                    date_generated=datetime(2024, 1, 1, 23, 59, 59, 999999),
                    input_oois=[
                        Reference("Hostname|internet|example3.com"),
                        Reference("Hostname|internet|example4.com"),
                    ],
                    report_id=UUID("1730b72f-b115-412e-ad44-dae6ab3edff9"),
                    organization_code="test_organization",
                    organization_name="Test Organization",
                    organization_tags=[],
                    data_raw_id="acbd2250-85f4-471a-ab70-ba1750280194",
                    observed_at=datetime(2024, 1, 1, 23, 59, 59, 999999),
                    parent_report=Reference("Report|e821aaeb-a6bd-427f-b064-e46837911a5d"),
                    has_parent=True,
                ),
                Report(
                    object_type="Report",
                    scan_profile=None,
                    primary_key="Report|463c7f72-fef9-42ef-baf9-f10fcfb91abf",
                    name="Safe Connections Report",
                    report_type="safe-connections-report",
                    template="safe_connections_report/report.html",
                    date_generated=datetime(2024, 1, 1, 23, 59, 59, 999999),
                    input_oois=[
                        Reference("Hostname|internet|example5.com"),
                        Reference("Hostname|internet|example6.com"),
                    ],
                    report_id=UUID("463c7f72-fef9-42ef-baf9-f10fcfb91abf"),
                    organization_code="test_organization",
                    organization_name="Test Organization",
                    organization_tags=[],
                    data_raw_id="ba2d86b8-aca8-4009-adc0-e3d59ea34906",
                    observed_at=datetime(2024, 1, 1, 23, 59, 59, 999999),
                    parent_report=Reference("Report|e821aaeb-a6bd-427f-b064-e46837911a5d"),
                    has_parent=True,
                ),
                Report(
                    object_type="Report",
                    scan_profile=None,
                    primary_key="Report|463c7f72-fef9-42ef-baf9-f10fcfb91abe",
                    name="Safe Connections Report",
                    report_type="safe-connections-report",
                    template="safe_connections_report/report.html",
                    date_generated=datetime(2024, 1, 1, 23, 59, 59, 999999),
                    input_oois=[
                        Reference("Hostname|internet|example7.com"),
                        Reference("Hostname|internet|example8.com"),
                    ],
                    report_id=UUID("463c7f72-fef9-42ef-baf9-f10fcfb91abe"),
                    organization_code="test_organization",
                    organization_name="Test Organization",
                    organization_tags=[],
                    data_raw_id="ba2d86b8-aca8-4009-adc0-e3d59ea34904",
                    observed_at=datetime(2024, 1, 1, 23, 59, 59, 999999),
                    parent_report=Reference("Report|e821aaeb-a6bd-427f-b064-e46837911a5d"),
                    has_parent=True,
                ),
            ],
        )
    ]


def onboarding_collect_data():
    return {
        "Hostname|internet|mispo.es": {
            "input_ooi": "Hostname|internet|mispo.es",
            "records": [
                {
                    "type": "A",
                    "ttl": 480,
                    "name": "mispo.es",
                    "content": "134.209.85.72",
                },
                {
                    "type": "MX",
                    "ttl": 480,
                    "name": "mispo.es",
                    "content": "10 mx.wijmailenveilig.nl.",
                },
                {
                    "type": "NS",
                    "ttl": 480,
                    "name": "mispo.es",
                    "content": "ns1.domaindiscount24.net.",
                },
                {
                    "type": "NS",
                    "ttl": 480,
                    "name": "mispo.es",
                    "content": "ns2.domaindiscount24.net.",
                },
                {
                    "type": "NS",
                    "ttl": 480,
                    "name": "mispo.es",
                    "content": "ns3.domaindiscount24.net.",
                },
                {
                    "type": "SOA",
                    "ttl": 480,
                    "name": "mispo.es",
                    "content": "ns1.domaindiscount24.net. tech.key-systems.net. 2023012324 10800 3600 604800 3600",
                },
            ],
            "security": {"spf": False, "dkim": False, "dmarc": False, "dnssec": False, "caa": False},
            "finding_types": [],
        }
    }


@pytest.fixture
def rocky_health():
    ServiceHealth(
        service="rocky",
        healthy=True,
        version="0.0.1.dev1",
        additional=None,
        results=[
            ServiceHealth(
                service="octopoes",
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
            ),
            ServiceHealth(service="katalogus", healthy=True, version="0.0.1-development", additional=None, results=[]),
            ServiceHealth(service="scheduler", healthy=True, version="0.0.1.dev1", additional=None, results=[]),
            ServiceHealth(service="bytes", healthy=True, version="0.0.1.dev1", additional=None, results=[]),
            ServiceHealth(service="keiko", healthy=True, version="0.0.1.dev1", additional=None, results=[]),
        ],
    )


@pytest.fixture
def boefje_dns_records():
    return Boefje(
        id="dns-records",
        name="DnsRecords",
        version=None,
        authors=None,
        created=None,
        description="Fetch the DNS record(s) of a hostname",
        related=[],
        enabled=True,
        type="boefje",
        scan_level=SCAN_LEVEL.L1,
        consumes={Hostname},
        options=None,
        runnable_hash=None,
        produces={"boefje/dns-records"},
        boefje_schema={},
        oci_image="ghcr.io/test/image:123",
        oci_arguments=["-test", "-arg"],
    )


@pytest.fixture
def boefje_nmap_tcp():
    return Boefje(
        id="nmap",
        name="Nmap TCP",
        version=None,
        authors=None,
        created=None,
        description="Defaults to top 250 TCP ports. Includes service detection.",
        environment_keys=None,
        related=[],
        enabled=True,
        type="boefje",
        scan_level=SCAN_LEVEL.L2,
        consumes={IPAddressV4, IPAddressV6},
        options=None,
        runnable_hash=None,
        produces={"boefje/nmap"},
        boefje_schema={},
        oci_image="ghcr.io/test/image:123",
        oci_arguments=["-test", "-arg"],
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


@pytest.fixture
def get_aggregate_report_ooi():
    return Report(
        object_type="Report",
        scan_profile=EmptyScanProfile(
            scan_profile_type="empty",
            reference=Reference("Report|6a073ba0-46d3-451c-a7f8-46923c2b841b"),
            level=ScanLevel.L0,
            user_id=None,
        ),
        primary_key="Report|6a073ba0-46d3-451c-a7f8-46923c2b841b",
        name="Aggregate Report",
        report_type="aggregate-organisation-report",
        template="aggregate_organisation_report/report.html",
        date_generated=datetime(2024, 9, 3, 14, 14, 46, 999999),
        input_oois=["Hostname|internet|mispo.es"],
        report_id=UUID("6a073ba0-46d3-451c-a7f8-46923c2b841b"),
        organization_code="_test",
        organization_name="Test Organization",
        organization_tags=[],
        data_raw_id="250cf43e-bfe2-4249-b493-a12921cb79f6",
        observed_at=datetime(2024, 9, 3, 14, 14, 45, 999999),
        parent_report=None,
        has_parent=False,
    )


@pytest.fixture
def get_aggregate_report_from_bytes():
    data = {
        "systems": {
            "services": {
                "IPAddressV4|internet|134.209.85.72": {"hostnames": ["Hostname|internet|mispo.es"], "services": []}
            }
        },
        "services": {},
        "recommendations": [],
        "recommendation_counts": {},
        "open_ports": {"134.209.85.72": {"ports": {}, "hostnames": ["mispo.es"], "services": {}}},
        "ipv6": {"mispo.es": {"enabled": False, "systems": []}},
        "vulnerabilities": {
            "IPAddressV4|internet|134.209.85.72": {
                "hostnames": "(mispo.es)",
                "vulnerabilities": {},
                "summary": {"total_findings": 0, "total_criticals": 0, "terms": [], "recommendations": []},
                "title": "134.209.85.72",
            }
        },
        "basic_security": {
            "rpki": {},
            "system_specific": {"Mail": [], "Web": [], "DNS": []},
            "safe_connections": {},
            "summary": {},
        },
        "summary": {"Critical vulnerabilities": 0, "IPs scanned": 1, "Hostnames scanned": 1, "Terms in report": ""},
        "total_findings": 0,
        "total_systems": 1,
        "total_hostnames": 1,
        "total_systems_basic_security": 0,
        "health": [
            {"service": "rocky", "healthy": True, "version": "0.0.1.dev1", "additional": None, "results": []},
            {"service": "octopoes", "healthy": True, "version": "0.0.1.dev1", "additional": None, "results": []},
            {
                "service": "xtdb",
                "healthy": True,
                "version": "1.24.1",
                "additional": {
                    "version": "1.24.1",
                    "revision": "1164f9a3c7e36edbc026867945765fd4366c1731",
                    "indexVersion": 22,
                    "consumerState": None,
                    "kvStore": "xtdb.rocksdb.RocksKv",
                    "estimateNumKeys": 36846,
                    "size": 33301692,
                },
                "results": [],
            },
            {
                "service": "katalogus",
                "healthy": True,
                "version": "0.0.1-development",
                "additional": None,
                "results": [],
            },
            {"service": "scheduler", "healthy": True, "version": "0.0.1.dev1", "additional": None, "results": []},
            {"service": "bytes", "healthy": True, "version": "0.0.1.dev1", "additional": None, "results": []},
            {"service": "keiko", "healthy": True, "version": "0.0.1.dev1", "additional": None, "results": []},
        ],
        "config_oois": [],
        "plugins": [
            {
                "required": True,
                "enabled": False,
                "name": "SSLCertificates",
                "scan_level": 1,
                "type": "boefje",
                "description": "Scan SSL certificates of websites",
            },
            {
                "required": True,
                "enabled": False,
                "name": "Security.txt downloader",
                "scan_level": 2,
                "type": "boefje",
                "description": "Downloads the security.txt file from the target host.",
            },
            {
                "required": True,
                "enabled": False,
                "name": "WebpageAnalysis",
                "scan_level": 2,
                "type": "boefje",
                "description": "Downloads a resource and uses several different normalizers to analyze",
            },
            {
                "required": True,
                "enabled": False,
                "name": "SSLScan",
                "scan_level": 2,
                "type": "boefje",
                "description": "Scan SSL/TLS versions of websites",
            },
            {
                "required": True,
                "enabled": False,
                "name": "RPKI",
                "scan_level": 1,
                "type": "boefje",
                "description": "Check if an IPv4 or IPv6 address has a valid VRPS record.",
            },
            {
                "required": True,
                "enabled": False,
                "name": "Nmap TCP",
                "scan_level": 2,
                "type": "boefje",
                "description": "Defaults to top 250 TCP ports. Includes service detection.",
            },
            {
                "required": True,
                "enabled": True,
                "name": "DnsRecords",
                "scan_level": 1,
                "type": "boefje",
                "description": "Fetch the DNS record(s) of a hostname",
            },
            {
                "required": True,
                "enabled": False,
                "name": "Testssl.sh Ciphers",
                "scan_level": 2,
                "type": "boefje",
                "description": "Run testssl.sh Docker container and check ciphers",
            },
            {
                "required": True,
                "enabled": True,
                "name": "Dnssec",
                "scan_level": 1,
                "type": "boefje",
                "description": "Validates DNSSec of a hostname",
            },
            {
                "required": False,
                "enabled": False,
                "name": "masscan",
                "scan_level": 2,
                "type": "boefje",
                "description": "Quickly scan large amounts of IPs.",
            },
            {
                "required": False,
                "enabled": False,
                "name": "Nmap IP range",
                "scan_level": 2,
                "type": "boefje",
                "description": "Scan an IP range and store found IPs. Defaults to top-250 TCP and top-10 UDP on ranges "
                "with 1024 addresses or less. Larger ranges are skipped by default.",
            },
            {
                "required": False,
                "enabled": False,
                "name": "Shodan",
                "scan_level": 1,
                "type": "boefje",
                "description": "Use Shodan to find open ports with vulnerabilities that are found on that port",
            },
            {
                "required": False,
                "enabled": False,
                "name": "Nmap UDP",
                "scan_level": 2,
                "type": "boefje",
                "description": "Defaults to top 250 UDP ports. Includes service detection.",
            },
            {
                "required": False,
                "enabled": False,
                "name": "Nmap Ports",
                "scan_level": 2,
                "type": "boefje",
                "description": "Scan a specific set of ports including service detection",
            },
        ],
        "oois": [{"name": "mispo.es", "type": "Hostname", "scan_profile_level": 1, "scan_profile_type": "declared"}],
        "report_types": [
            {
                "name": "IPv6 Report",
                "description": "Check whether hostnames point to IPv6 addresses.",
                "label_style": "4-light",
            },
            {
                "name": "Mail Report",
                "description": "System specific Mail Report that focusses on IP addresses and hostnames.",
                "label_style": "2-light",
            },
            {
                "name": "Name Server Report",
                "description": "Name Server Report checks name servers on basic security standards.",
                "label_style": "1-light",
            },
            {"name": "Open Ports Report", "description": "Find open ports of IP addresses", "label_style": "5-light"},
            {
                "name": "RPKI Report",
                "description": "Shows whether the IP is covered by a valid RPKI ROA. For a hostname it shows the IP "
                "addresses and whether they are covered by a valid RPKI ROA.",
                "label_style": "4-light",
            },
            {
                "name": "Safe Connections Report",
                "description": "Shows whether the IPService contains safe ciphers.",
                "label_style": "2-light",
            },
            {
                "name": "System Report",
                "description": "Combine IP addresses, hostnames and services into systems.",
                "label_style": "6-light",
            },
            {
                "name": "Vulnerability Report",
                "description": "Vulnerabilities found are grouped for each system.",
                "label_style": "5-light",
            },
            {
                "name": "Web System Report",
                "description": "Web System Reports check web systems on basic security standards.",
                "label_style": "3-light",
            },
        ],
    }
    return json.dumps(data).encode("utf-8")
