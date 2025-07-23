import uuid
from collections.abc import Iterator
from datetime import datetime, timezone
from ipaddress import ip_address

import pytest

from octopoes.api.models import Declaration, Observation
from octopoes.config.settings import Settings
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.core.app import get_xtdb_client
from octopoes.core.service import OctopoesService
from octopoes.models import OOI, DeclaredScanProfile, Reference
from octopoes.models.ooi.certificate import X509Certificate
from octopoes.models.ooi.dns.zone import Hostname, ResolvedHostname
from octopoes.models.ooi.findings import CVEFindingType, Finding, KATFindingType, RetireJSFindingType, RiskLevelSeverity
from octopoes.models.ooi.network import IPAddressV4, IPAddressV6, IPPort, Network
from octopoes.models.ooi.reports import AssetReport, Report, ReportRecipe
from octopoes.models.ooi.service import IPService, Service
from octopoes.models.ooi.software import Software, SoftwareInstance
from octopoes.models.ooi.web import URL, HostnameHTTPURL, HTTPHeader, HTTPResource, SecurityTXT, Website
from octopoes.models.origin import Origin, OriginType
from octopoes.repositories.ooi_repository import XTDBOOIRepository
from octopoes.repositories.origin_parameter_repository import XTDBOriginParameterRepository
from octopoes.repositories.origin_repository import XTDBOriginRepository
from octopoes.repositories.scan_profile_repository import XTDBScanProfileRepository
from octopoes.xtdb.client import XTDBHTTPClient, XTDBSession
from openkat.models import Organization
from reports.runner.report_runner import LocalReportRunner
from tests.conftest import create_organization


@pytest.fixture
def valid_time():
    return datetime.now(timezone.utc)


@pytest.fixture
def katalogus_mock(mocker):
    katalogus = mocker.patch("katalogus.client.KATalogusClient")

    return katalogus


@pytest.fixture
def integration_organization(katalogus_mock, mocker, request) -> Organization:
    mocker.patch("openkat.settings.OCTOPOES_FACTORY")

    test_node = f"test-{request.node.originalname}"

    return Organization.objects.create(name="Test", code=test_node)


@pytest.fixture
def integration_organization_2(request) -> Organization:
    test_node = f"test-{request.node.originalname}-2"

    return Organization.objects.create(name="Test 2", code=test_node)


@pytest.fixture
def report_runner(valid_time) -> LocalReportRunner:
    return LocalReportRunner(valid_time)


@pytest.fixture
def app_settings():
    return Settings()


@pytest.fixture
def xtdb_http_client(app_settings: Settings) -> XTDBHTTPClient:
    test_node = "test"
    client = get_xtdb_client(str(app_settings.xtdb_uri), test_node)

    return client


@pytest.fixture
def xtdb_http_client_2(app_settings: Settings) -> XTDBHTTPClient:
    test_node = "test 2"
    client = get_xtdb_client(str(app_settings.xtdb_uri), test_node)

    return client


@pytest.fixture
def xtdb_session(xtdb_http_client: XTDBHTTPClient) -> Iterator[XTDBSession]:
    xtdb_http_client.create_node()
    create_organization(f"Test Organization {xtdb_http_client.client}", xtdb_http_client.client)

    yield XTDBSession(xtdb_http_client)

    xtdb_http_client.delete_node()


@pytest.fixture
def xtdb_session_2(xtdb_http_client_2: XTDBHTTPClient) -> Iterator[XTDBSession]:
    xtdb_http_client_2.create_node()
    create_organization(f"Test Organization {xtdb_http_client_2.client}" + "2", xtdb_http_client_2.client + "2")

    yield XTDBSession(xtdb_http_client_2)

    xtdb_http_client_2.delete_node()


class MockEventManager:
    def __init__(self):
        self.queue = []
        self.processed = [0]
        self.client = "test"

    def publish(self, event) -> None:
        self.queue.append(event)

    def publish_now(self, event, session) -> None:
        self.queue.append(event)

    def unprocessed(self) -> list:
        retval = self.queue[self.processed[-1] :]
        self.processed.append(len(self.queue))
        return retval

    def process_events(self, xtdb_octopoes_service: OctopoesService) -> int:
        targets = self.unprocessed()
        for event in targets:
            xtdb_octopoes_service.process_event(event)
        xtdb_octopoes_service.commit()
        return len(targets)

    def complete_process_events(self, xtdb_octopoes_service: OctopoesService, repeat: int = 3) -> int:
        retval = 0
        for _ in range(repeat):
            while True:
                val = self.process_events(xtdb_octopoes_service)
                if val == 0:
                    break
                retval += val
        return retval


@pytest.fixture
def event_manager(xtdb_session: XTDBSession) -> MockEventManager:
    return MockEventManager()


@pytest.fixture
def xtdb_ooi_repository(
    xtdb_session: XTDBSession, event_manager, xtdb_scan_profile_repository
) -> Iterator[XTDBOOIRepository]:
    yield XTDBOOIRepository(event_manager, xtdb_session, xtdb_scan_profile_repository)


@pytest.fixture
def xtdb_origin_repository(xtdb_session: XTDBSession, event_manager) -> Iterator[XTDBOriginRepository]:
    yield XTDBOriginRepository(event_manager, xtdb_session)


@pytest.fixture
def xtdb_origin_parameter_repository(
    xtdb_session: XTDBSession, event_manager
) -> Iterator[XTDBOriginParameterRepository]:
    yield XTDBOriginParameterRepository(event_manager, xtdb_session)


@pytest.fixture
def xtdb_scan_profile_repository(xtdb_session: XTDBSession, event_manager) -> Iterator[XTDBScanProfileRepository]:
    yield XTDBScanProfileRepository(event_manager, xtdb_session)


@pytest.fixture
def xtdb_octopoes_service(
    xtdb_ooi_repository: XTDBOOIRepository,
    xtdb_origin_repository: XTDBOriginRepository,
    xtdb_origin_parameter_repository: XTDBOriginParameterRepository,
    xtdb_scan_profile_repository: XTDBScanProfileRepository,
) -> OctopoesService:
    return OctopoesService(
        xtdb_ooi_repository, xtdb_origin_repository, xtdb_origin_parameter_repository, xtdb_scan_profile_repository
    )


@pytest.fixture
def xtdb_octopoes_api_connector(xtdb_session: XTDBSession, app_settings) -> OctopoesAPIConnector:
    return OctopoesAPIConnector(xtdb_session.client.client, app_settings)


@pytest.fixture
def xtdb_octopoes_api_connector_2(xtdb_session_2: XTDBSession, app_settings) -> OctopoesAPIConnector:
    return OctopoesAPIConnector(xtdb_session_2.client.client, app_settings)


def seed_system_with_xtdb(
    xtdb_ooi_repository: XTDBOOIRepository, xtdb_origin_repository: XTDBOriginRepository, valid_time
):
    network = Network(name="test")

    hostnames = [
        Hostname(network=network.reference, name="example.com"),
        Hostname(network=network.reference, name="a.example.com"),
        Hostname(network=network.reference, name="b.example.com"),
        Hostname(network=network.reference, name="c.example.com"),
        Hostname(network=network.reference, name="d.example.com"),
        Hostname(network=network.reference, name="e.example.com"),
        Hostname(network=network.reference, name="f.example.com"),
    ]

    addresses = [
        IPAddressV4(network=network.reference, address=ip_address("192.0.2.3")),
        IPAddressV6(network=network.reference, address=ip_address("3e4d:64a2:cb49:bd48:a1ba:def3:d15d:9230")),
    ]
    ports = [
        IPPort(address=addresses[0].reference, protocol="tcp", port=25),
        IPPort(address=addresses[0].reference, protocol="tcp", port=443),
        IPPort(address=addresses[0].reference, protocol="tcp", port=22),
        IPPort(address=addresses[1].reference, protocol="tcp", port=80),
    ]
    services = [Service(name="smtp"), Service(name="https"), Service(name="http"), Service(name="ssh")]
    ip_services = [
        IPService(ip_port=ports[0].reference, service=services[0].reference),
        IPService(ip_port=ports[1].reference, service=services[1].reference),
        IPService(ip_port=ports[2].reference, service=services[3].reference),
        IPService(ip_port=ports[3].reference, service=services[2].reference),
    ]

    resolved_hostnames = [
        ResolvedHostname(hostname=hostnames[0].reference, address=addresses[0].reference),  # ipv4
        ResolvedHostname(hostname=hostnames[0].reference, address=addresses[1].reference),  # ipv6
        ResolvedHostname(hostname=hostnames[1].reference, address=addresses[0].reference),
        ResolvedHostname(hostname=hostnames[2].reference, address=addresses[0].reference),
        ResolvedHostname(hostname=hostnames[3].reference, address=addresses[0].reference),
        ResolvedHostname(hostname=hostnames[4].reference, address=addresses[0].reference),
        ResolvedHostname(hostname=hostnames[5].reference, address=addresses[0].reference),
        ResolvedHostname(hostname=hostnames[3].reference, address=addresses[1].reference),
        ResolvedHostname(hostname=hostnames[4].reference, address=addresses[1].reference),
        ResolvedHostname(hostname=hostnames[6].reference, address=addresses[1].reference),
    ]
    certificates = [
        X509Certificate(
            subject="example.com",
            valid_from="2022-11-15T08:52:57",
            valid_until="2030-11-15T08:52:57",
            serial_number="abc123",
        )
    ]
    websites = [
        Website(ip_service=ip_services[0].reference, hostname=hostnames[0].reference, certificates=certificates[0]),
        Website(ip_service=ip_services[0].reference, hostname=hostnames[1].reference),
    ]
    software = [Software(name="DICOM")]
    instance = [SoftwareInstance(ooi=ports[0].reference, software=software[0].reference)]

    web_urls = [
        HostnameHTTPURL(netloc=hostnames[0].reference, path="/", scheme="http", network=network.reference, port=80),
        HostnameHTTPURL(netloc=hostnames[0].reference, path="/", scheme="https", network=network.reference, port=443),
    ]
    urls = [URL(network=network.reference, raw="https://test.com/security", web_url=web_urls[1].reference)]
    resources = [
        HTTPResource(website=websites[0].reference, web_url=web_urls[0].reference),
        HTTPResource(website=websites[0].reference, web_url=web_urls[1].reference),
    ]
    headers = [HTTPHeader(resource=resources[1].reference, key="test key", value="test value")]
    security_txts = [SecurityTXT(website=websites[1].reference, url=urls[0].reference, security_txt="test text")]
    finding_types = [
        KATFindingType(id="KAT-NO-CSP"),
        KATFindingType(id="KAT-CSP-VULNERABILITIES"),
        KATFindingType(id="KAT-NO-HTTPS-REDIRECT"),
        KATFindingType(id="KAT-NO-CERTIFICATE"),
        KATFindingType(id="KAT-CERTIFICATE-EXPIRED"),
        KATFindingType(id="KAT-CERTIFICATE-EXPIRING-SOON"),
    ]
    findings = [
        Finding(finding_type=finding_types[0].reference, ooi=resources[0].reference),
        Finding(finding_type=finding_types[2].reference, ooi=web_urls[0].reference),
        Finding(finding_type=finding_types[3].reference, ooi=websites[1].reference),
        Finding(finding_type=finding_types[4].reference, ooi=certificates[0].reference),
    ]

    oois = (
        hostnames
        + addresses
        + ports
        + services
        + ip_services
        + resolved_hostnames
        + websites
        + software
        + instance
        + web_urls
        + resources
        + headers
        + finding_types
        + findings
        + urls
        + security_txts
        + certificates
    )

    network_origin = Origin(
        origin_type=OriginType.DECLARATION,
        method="kat_manual_csv",
        source=network.reference,
        source_method="manual",
        result=[network.reference],
        task_id=uuid.uuid4(),
    )
    xtdb_ooi_repository.save(network, valid_time=valid_time)
    xtdb_origin_repository.save(network_origin, valid_time=valid_time)

    origin = Origin(
        origin_type=OriginType.OBSERVATION,
        method="",
        source=network.reference,
        source_method="manual",
        result=[ooi.reference for ooi in oois],
        task_id=uuid.uuid4(),
    )

    for ooi in oois:
        xtdb_ooi_repository.save(ooi, valid_time=valid_time)

    xtdb_origin_repository.save(origin, valid_time=valid_time)

    xtdb_origin_repository.commit()
    xtdb_ooi_repository.commit()


def seed_report(
    name: str, valid_time, ooi_repository, origin_repository, input_reports: list[AssetReport] | None = None
) -> Report:
    recipe = ReportRecipe(
        report_type="concatenated-report",
        recipe_id=uuid.uuid4(),
        report_name_format="test",
        cron_expression="* * * *",
        input_recipe={},
        asset_report_types=[],
    )
    report = Report(
        name=name,
        date_generated=valid_time,
        organization_code="code",
        organization_name="name",
        organization_tags=["tag1", "tag2"],
        data_raw_id="raw",
        observed_at=valid_time,
        reference_date=valid_time,
        report_recipe=recipe.reference,
        input_oois=[input_report.reference for input_report in input_reports] if input_reports else [],
        report_type="concatenated-report",
    )
    report_origin = Origin(
        origin_type=OriginType.DECLARATION,
        method="manual",
        source=report.reference,
        result=[report.reference],
        task_id=uuid.uuid4(),
    )
    recipe_origin = Origin(
        origin_type=OriginType.DECLARATION,
        method="manual",
        source=recipe.reference,
        result=[recipe.reference],
        task_id=uuid.uuid4(),
    )

    ooi_repository.save(recipe, valid_time=valid_time)
    origin_repository.save(recipe_origin, valid_time=valid_time)

    ooi_repository.save(report, valid_time=valid_time)
    origin_repository.save(report_origin, valid_time=valid_time)

    origin_repository.commit()
    ooi_repository.commit()

    return report


def seed_asset_report(
    name: str, valid_time, ooi_repository, origin_repository, input_ooi: str = "testref"
) -> AssetReport:
    recipe = ReportRecipe(
        report_type="concatenated-report",
        recipe_id=uuid.uuid4(),
        report_name_format="test",
        cron_expression="* * * *",
        input_recipe={},
        asset_report_types=[],
    )

    asset_report = AssetReport(
        name=name,
        date_generated=valid_time,
        report_recipe=recipe.reference,
        organization_code="code",
        organization_name="name",
        organization_tags=["tag1", "tag2"],
        data_raw_id="raw",
        reference_date=valid_time,
        observed_at=valid_time,
        input_ooi=input_ooi,
        report_type="system-report",
    )
    report_origin = Origin(
        origin_type=OriginType.DECLARATION,
        method="manual",
        source=asset_report.reference,
        result=[asset_report.reference],
        task_id=uuid.uuid4(),
    )
    recipe_origin = Origin(
        origin_type=OriginType.DECLARATION,
        method="manual",
        source=recipe.reference,
        result=[recipe.reference],
        task_id=uuid.uuid4(),
    )

    ooi_repository.save(recipe, valid_time=valid_time)
    origin_repository.save(recipe_origin, valid_time=valid_time)

    ooi_repository.save(asset_report, valid_time=valid_time)
    origin_repository.save(report_origin, valid_time=valid_time)

    origin_repository.commit()
    ooi_repository.commit()

    return asset_report


def seed_system(
    octopoes_api_connector: OctopoesAPIConnector,
    valid_time: datetime,
    test_hostname: str = "example.com",
    test_ip: str = "192.0.2.3",
    test_ipv6: str = "3e4d:64a2:cb49:bd48:a1ba:def3:d15d:9230",
) -> dict[str, list[OOI]]:
    network = Network(name="test")
    octopoes_api_connector.save_declaration(Declaration(ooi=network, valid_time=valid_time))

    hostnames = [
        Hostname(network=network.reference, name=test_hostname),
        Hostname(network=network.reference, name=f"a.{test_hostname}"),
        Hostname(network=network.reference, name=f"b.{test_hostname}"),
        Hostname(network=network.reference, name=f"c.{test_hostname}"),
        Hostname(network=network.reference, name=f"d.{test_hostname}"),
        Hostname(network=network.reference, name=f"e.{test_hostname}"),
        Hostname(network=network.reference, name=f"f.{test_hostname}"),
    ]

    addresses = [
        IPAddressV4(network=network.reference, address=ip_address(test_ip)),
        IPAddressV6(network=network.reference, address=ip_address(test_ipv6)),
    ]
    ports = [
        IPPort(address=addresses[0].reference, protocol="tcp", port=25),
        IPPort(address=addresses[0].reference, protocol="tcp", port=443),
        IPPort(address=addresses[0].reference, protocol="tcp", port=22),
        IPPort(address=addresses[1].reference, protocol="tcp", port=80),
    ]
    services = [Service(name="smtp"), Service(name="https"), Service(name="http"), Service(name="ssh")]
    ip_services = [
        IPService(ip_port=ports[0].reference, service=services[0].reference),
        IPService(ip_port=ports[1].reference, service=services[1].reference),
        IPService(ip_port=ports[2].reference, service=services[3].reference),
        IPService(ip_port=ports[3].reference, service=services[2].reference),
    ]

    resolved_hostnames = [
        ResolvedHostname(hostname=hostnames[0].reference, address=addresses[0].reference),  # ipv4
        ResolvedHostname(hostname=hostnames[0].reference, address=addresses[1].reference),  # ipv6
        ResolvedHostname(hostname=hostnames[1].reference, address=addresses[0].reference),
        ResolvedHostname(hostname=hostnames[2].reference, address=addresses[0].reference),
        ResolvedHostname(hostname=hostnames[3].reference, address=addresses[0].reference),
        ResolvedHostname(hostname=hostnames[4].reference, address=addresses[0].reference),
        ResolvedHostname(hostname=hostnames[5].reference, address=addresses[0].reference),
        ResolvedHostname(hostname=hostnames[3].reference, address=addresses[1].reference),
        ResolvedHostname(hostname=hostnames[4].reference, address=addresses[1].reference),
        ResolvedHostname(hostname=hostnames[6].reference, address=addresses[1].reference),
    ]
    certificates = [
        X509Certificate(
            subject=test_hostname,
            valid_from="2022-11-15T08:52:57",
            valid_until="2030-11-15T08:52:57",
            serial_number="abc123",
        )
    ]
    websites = [
        Website(ip_service=ip_services[0].reference, hostname=hostnames[0].reference, certificates=certificates[0]),
        Website(ip_service=ip_services[0].reference, hostname=hostnames[1].reference),
    ]
    software = [Software(name="DICOM")]

    web_urls = [
        HostnameHTTPURL(netloc=hostnames[0].reference, path="/", scheme="http", network=network.reference, port=80),
        HostnameHTTPURL(netloc=hostnames[0].reference, path="/", scheme="https", network=network.reference, port=443),
    ]
    instances = [
        SoftwareInstance(ooi=ports[0].reference, software=software[0].reference),
        SoftwareInstance(ooi=web_urls[0].reference, software=software[0].reference),
    ]

    urls = [URL(network=network.reference, raw="https://test.com/security", web_url=web_urls[1].reference)]
    resources = [
        HTTPResource(website=websites[0].reference, web_url=web_urls[0].reference),
        HTTPResource(website=websites[0].reference, web_url=web_urls[1].reference),
    ]
    headers = [HTTPHeader(resource=resources[1].reference, key="test key", value="test value")]
    security_txts = [
        SecurityTXT(website=websites[0].reference, url=urls[0].reference, security_txt="test text"),
        SecurityTXT(website=websites[1].reference, url=urls[0].reference, security_txt="test text"),
    ]
    finding_types = [
        KATFindingType(
            id="KAT-NO-CSP", risk_severity=RiskLevelSeverity.MEDIUM, description="test", recommendation="csp test"
        ),
        KATFindingType(id="KAT-CSP-VULNERABILITIES", risk_severity=RiskLevelSeverity.MEDIUM, description="test"),
        KATFindingType(id="KAT-NO-HTTPS-REDIRECT", risk_severity=RiskLevelSeverity.MEDIUM, description="test"),
        KATFindingType(id="KAT-NO-CERTIFICATE", risk_severity=RiskLevelSeverity.MEDIUM, description="test"),
        KATFindingType(id="KAT-CERTIFICATE-EXPIRED", risk_severity=RiskLevelSeverity.MEDIUM, description="test"),
        KATFindingType(id="KAT-CERTIFICATE-EXPIRING-SOON", risk_severity=RiskLevelSeverity.MEDIUM, description="test"),
        CVEFindingType(id="CVE-2019-8331", risk_severity=RiskLevelSeverity.MEDIUM, description="test"),
        CVEFindingType(id="CVE-2018-20677", risk_severity=RiskLevelSeverity.MEDIUM, description="test"),
        RetireJSFindingType(
            id="RetireJS-jquerymigrate-f3a3", risk_severity=RiskLevelSeverity.MEDIUM, description="test"
        ),
    ]

    findings = [
        Finding(finding_type=finding_types[-3].reference, ooi=instances[1].reference),
        Finding(finding_type=finding_types[-2].reference, ooi=instances[1].reference),
        Finding(finding_type=finding_types[-1].reference, ooi=instances[1].reference),
    ]

    oois = (
        hostnames
        + addresses
        + ports
        + services
        + ip_services
        + resolved_hostnames
        + websites
        + software
        + instances
        + web_urls
        + resources
        + headers
        + finding_types
        + findings
        + urls
        + security_txts
        + certificates
    )

    octopoes_api_connector.save_observation(
        Observation(
            method="",
            source_method="test",
            source=network.reference,
            task_id=uuid.uuid4(),
            valid_time=valid_time,
            result=oois,
        )
    )

    return {
        "hostnames": hostnames,
        "addresses": addresses,
        "ports": ports,
        "services": services,
        "ip_services": ip_services,
        "resolved_hostnames": resolved_hostnames,
        "websites": websites,
        "software": software,
        "instances": instances,
        "web_urls": web_urls,
        "resources": resources,
        "headers": headers,
        "finding_types": finding_types,
        "urls": urls,
        "security_txts": security_txts,
        "certificates": certificates,
    }


@pytest.fixture()
def hostname_oois():
    return [
        Hostname(
            object_type="Hostname",
            scan_profile=DeclaredScanProfile(
                scan_profile_type="declared", reference=Reference("Hostname|test|example.com"), level=2
            ),
            primary_key="Hostname|test|example.com",
            network=Reference("Network|test"),
            name="example.com",
            dns_zone=Reference("DNSZone|test|example.com"),
            registered_domain=None,
        ).reference
    ]
