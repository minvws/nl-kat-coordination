import uuid
from datetime import datetime, timezone
from ipaddress import ip_address

import pytest
from django.conf import settings
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from octopoes.api.models import Declaration, Observation
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models.ooi.certificate import X509Certificate
from octopoes.models.ooi.dns.zone import Hostname, ResolvedHostname
from octopoes.models.ooi.findings import CVEFindingType, KATFindingType, RetireJSFindingType, RiskLevelSeverity
from octopoes.models.ooi.network import IPAddressV4, IPAddressV6, IPPort, Network
from octopoes.models.ooi.service import IPService, Service
from octopoes.models.ooi.software import Software, SoftwareInstance
from octopoes.models.ooi.web import URL, HostnameHTTPURL, HTTPHeader, HTTPResource, SecurityTXT, Website


@pytest.fixture
def valid_time():
    return datetime.now(timezone.utc)


@pytest.fixture
def octopoes_api_connector(request) -> OctopoesAPIConnector:
    test_node = f"test-{request.node.originalname}"

    connector = OctopoesAPIConnector(settings.OCTOPOES_API, test_node)
    connector.session.mount("http://", HTTPAdapter(max_retries=Retry(total=3, backoff_factor=1)))

    connector.create_node()
    yield connector
    connector.delete_node()


@pytest.fixture
def octopoes_api_connector_2(request) -> OctopoesAPIConnector:
    test_node = f"test-{request.node.originalname}-2"

    connector = OctopoesAPIConnector(settings.OCTOPOES_API, test_node)
    connector.session.mount("http://", HTTPAdapter(max_retries=Retry(total=3, backoff_factor=1)))

    connector.create_node()
    yield connector
    connector.delete_node()


def seed_system(
    octopoes_api_connector: OctopoesAPIConnector,
    valid_time: datetime,
    test_hostname: str = "example.com",
    test_ip: str = "192.0.2.3",
):
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
        + urls
        + security_txts
        + certificates
    )

    octopoes_api_connector.save_observation(
        Observation(method="", source=network.reference, task_id=uuid.uuid4(), valid_time=valid_time, result=oois)
    )
    octopoes_api_connector.recalculate_bits()

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
