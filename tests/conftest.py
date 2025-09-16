import binascii
import json
import logging
import uuid
from collections.abc import Iterator
from datetime import datetime, timezone
from ipaddress import IPv4Address, IPv6Address
from os import urandom
from pathlib import Path
from unittest.mock import patch
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

from crisis_room.models import Dashboard, DashboardData
from files.models import File, GenericContent
from openkat.models import GROUP_ADMIN, GROUP_CLIENT, GROUP_REDTEAM, Indemnification, Organization, OrganizationMember
from openkat.views.health import ServiceHealth
from tasks.models import Schedule, TaskStatus
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
            scan_profile_type="declared", reference=Reference("URL|testnetwork|http://example.com/"), level=ScanLevel.L1
        ),
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
    return Website(ip_service=ip_service.reference, hostname=hostname.reference)


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
def cipher(ip_service: IPService) -> TLSCipher:
    return TLSCipher(
        ip_service=ip_service.reference,
        suites={
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
            ]
        },
    )


@pytest.fixture
def query_data_tls_findings_and_suites(cipher):
    return [
        Finding(
            ooi=cipher.reference,
            description="Fake description with cipher_suite_name ECDHE-RSA-AES128-SHA",
            finding_type=KATFindingType(id="KAT-RECOMMENDATION-BAD-CIPHER").reference,
        ),
        Finding(
            ooi=cipher.reference,
            description="Fake description with cipher_suite_name ECDHE-RSA-AES256-SHA",
            finding_type=KATFindingType(id="KAT-MEDIUM-BAD-CIPHER").reference,
        ),
        Finding(
            ooi=cipher.reference,
            description="Fake description...",
            finding_type=KATFindingType(id="KAT-CRITICAL-BAD-CIPHER").reference,
        ),
    ]


recipe = ReportRecipe(
    report_type="concatenated-report",
    recipe_id=uuid.uuid4(),
    report_name_format="test",
    cron_expression="* * * *",
    input_recipe={},
    asset_report_types=[],
)

parent_report = HydratedReport(
    report_recipe=recipe.reference,
    primary_key="Report|e821aaeb-a6bd-427f-b064-e46837911a5d",
    name="Test Parent Report",
    report_type="concatenated-report",
    template="report.html",
    date_generated=datetime(2024, 1, 1, 23, 59, 59, 999999),
    reference_date=datetime(2024, 1, 1, 23, 59, 59, 999999),
    input_oois=[],
    organization_code="test_organization",
    organization_name="Test Organization",
    organization_tags=[],
    data_raw_id="a5ccf97b-d4e9-442d-85bf-84e739b6d3ed",
    observed_at=datetime(2024, 1, 1, 23, 59, 59, 999999),
)


def create_asset_report(
    name,
    report_type,
    template,
    uuid_iterator: Iterator,
    input_ooi="Hostname|internet|example.com",
    organization_code: str = "test",
    organization_name: str = "Test Organization",
) -> AssetReport:
    return AssetReport(
        report_recipe=recipe.reference,
        name=name,
        report_type=report_type,
        template=template,
        date_generated=datetime(2024, 1, 1, 23, 59, 59, 999999),
        reference_date=datetime(2024, 1, 1, 23, 59, 59, 999999),
        input_ooi=input_ooi,
        organization_code=organization_code,
        organization_name=organization_name,
        organization_tags=[],
        data_raw_id=str(next(uuid_iterator)),
        observed_at=datetime(2024, 1, 1, 23, 59, 59, 999999),
    )


def create_report(
    name, report_type, template, asset_reports: list[AssetReport] | None, uuid_iterator: Iterator
) -> HydratedReport:
    if asset_reports is None:
        asset_reports = []

    return HydratedReport(
        report_recipe=recipe.reference,
        name=name,
        report_type=report_type,
        template=template,
        date_generated=datetime(2024, 1, 1, 23, 59, 59, 999999),
        reference_date=datetime(2024, 1, 1, 23, 59, 59, 999999),
        input_oois=asset_reports,
        organization_code="test",
        organization_name="Test Organization",
        organization_tags=[],
        data_raw_id=str(next(uuid_iterator)),
        observed_at=datetime(2024, 1, 1, 23, 59, 59, 999999),
    )


ids = iter(
    [
        UUID("acbd2250-85f4-471a-ab70-ba1750280194"),
        UUID("ba2d86b8-aca8-4009-adc0-e3d59ea34904"),
        UUID("3d2ea955-13c1-46f6-81f3-edfe72d8af0b"),
        UUID("fe4d0f5d-5447-47d3-952d-74544c8a9d8d"),
        UUID("3ca35c20-1139-4bf4-a11a-a0b83f3c48ff"),
        UUID("1e419bee-672f-4561-b3b9-f47bd6ce60b7"),
        UUID("1e419bee-672f-4561-b3b9-f47bd6ce60b7"),
    ]
)


assets = [
    create_asset_report("RPKI Report", "rpki-report", "rpki_report/report.html", ids),
    create_asset_report(
        "Safe Connections Report", "safe-connections-report", "safe_connections_report/report.html", ids
    ),
    create_asset_report("System Report", "systems-report", "systems_report/report.html", ids),
    create_asset_report("Mail Report", "mail-report", "mail_report/report.html", ids),
    create_asset_report("IPv6 Report", "ipv6-report", "ipv6_report/report.html", ids),
    create_asset_report("Web System Report", "web-system-report", "web_system_report/report.html", ids),
    create_asset_report("Web System Report", "web-system-report", "web_system_report/report.html", ids),
]

dns_report = create_asset_report(
    "DNS Report", "dns-report", "dns_report/report.html", iter(["a5ccf97b-d4e9-442d-85bf-84e739b63da9s"])
)


@pytest.fixture
def report_list_one_asset_report():
    uuids = iter(["acbd2250-85f4-471a-ab70-ba17502801e"])
    return [create_report("Concatenated test report", "concatenated-report", "report.html", [assets[0]], uuids)]


@pytest.fixture
def report_list_two_asset_reports():
    uuids = iter(["acbd2250-85f4-471a-ab70-ba17502801a"])
    return [
        create_report("Concatenated test report", "concatenated-report", "report.html", [assets[5], assets[6]], uuids)
    ]


@pytest.fixture
def report_list_six_asset_reports():
    uuids = iter(["acbd2250-85f4-471a-ab70-ba17502801a"])
    asset_reports = [assets[0], assets[1], assets[2], assets[3], assets[4], assets[5]]
    return [create_report("Concatenated test report", "concatenated-report", "report.html", asset_reports, uuids)]


@pytest.fixture
def get_asset_reports() -> list[tuple[str, Report]]:
    return [
        (parent_report.primary_key, assets[0]),
        (parent_report.primary_key, assets[1]),
        (parent_report.primary_key, assets[2]),
        (parent_report.primary_key, assets[3]),
        (parent_report.primary_key, assets[4]),
        (parent_report.primary_key, assets[5]),
    ]


@pytest.fixture
def report_recipe():
    return ReportRecipe(
        report_type="concatenated-report",
        recipe_id="744d054e-9c70-4f18-ad27-122cfc1b7903",
        report_name_format="Test Report Name Format",
        input_recipe={"input_oois": ["Hostname|internet|mispo.es"]},
        asset_report_types=["dns-report"],
        cron_expression="0 0 * * *",
    )


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


@pytest.fixture
def reports_task_list_db(organization):
    task_a = TaskDB.objects.create(
        organization=organization,
        status=TaskStatus.FAILED.value,
        type="report",
        data=ReportTask(
            type="report", organisation_id=organization.code, report_recipe_id="3f5c1a46-1969-49b7-b402-4676fb59ca4b"
        ).model_dump(mode="json"),
    )
    task_b = TaskDB.objects.create(
        organization=organization,
        status=TaskStatus.COMPLETED.value,
        type="report",
        data=ReportTask(
            type="report", organisation_id=organization.code, report_recipe_id="451a676d-91f8-4366-ac24-d1a47205181d"
        ).model_dump(mode="json"),
    )
    return [task_a, task_b]


@pytest.fixture
def dashboard_data(client_member, client_member_b):
    recipe_id_a = "7ebcdb32-e7f2-4c2d-840a-d7b8e6b37616"
    recipe_id_b = "c41bbf9a-7102-4b6b-b256-b3036e106316"

    dashboard_a, dashboard_b = Dashboard.objects.bulk_create(
        [
            Dashboard(name="Crisis Room Findings Dashboard", organization=client_member.organization),
            Dashboard(name="Crisis Room Findings Dashboard", organization=client_member_b.organization),
        ]
    )
    dashboard_data_a, dashboard_data_b = DashboardData.objects.bulk_create(
        [
            DashboardData(dashboard=dashboard_a, recipe=recipe_id_a, findings_dashboard=True),
            DashboardData(dashboard=dashboard_b, recipe=recipe_id_b, findings_dashboard=True),
        ]
    )

    return [dashboard_data_a, dashboard_data_b]


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
