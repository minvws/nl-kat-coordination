import multiprocessing
import uuid
from ipaddress import ip_address

import time
from datetime import datetime, timezone
from multiprocessing import Manager
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from octopoes.api.models import Observation, Declaration
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import OOI
from octopoes.models.ooi.certificate import X509Certificate
from octopoes.models.ooi.dns.zone import ResolvedHostname, Hostname
from octopoes.models.ooi.findings import Finding, RetireJSFindingType, CVEFindingType, KATFindingType, RiskLevelSeverity
from octopoes.models.ooi.network import IPAddressV4, IPPort, IPAddressV6, Network
from octopoes.models.ooi.service import IPService, Service
from octopoes.models.ooi.software import SoftwareInstance, Software
from octopoes.models.ooi.web import SecurityTXT, HTTPHeader, HTTPResource, URL, Website, HostnameHTTPURL
from pydantic import TypeAdapter

from boefjes.app import SchedulerWorkerManager
from boefjes.clients.scheduler_client import Queue, QueuePrioritizedItem, SchedulerClientInterface, Task, TaskStatus
from boefjes.config import Settings, settings
from boefjes.job_models import BoefjeMeta, NormalizerMeta
from boefjes.runtime_interfaces import Handler, WorkerManager
from tests.loading import get_dummy_data


class MockSchedulerClient(SchedulerClientInterface):
    def __init__(
        self,
        queue_response: bytes,
        boefje_responses: list[bytes],
        normalizer_responses: list[bytes],
        log_path: Path,
        raise_on_empty_queue: Exception = KeyboardInterrupt,
        iterations_to_wait_for_exception: int = 0,
        sleep_time: int = 0.1,
    ):
        self.queue_response = queue_response
        self.boefje_responses = boefje_responses
        self.normalizer_responses = normalizer_responses
        self.log_path = log_path
        self.raise_on_empty_queue = raise_on_empty_queue
        self.iterations_to_wait_for_exception = iterations_to_wait_for_exception
        self.sleep_time = sleep_time

        self._iterations = 0
        self._tasks: dict[str, Task] = multiprocessing.Manager().dict()
        self._popped_items: dict[str, QueuePrioritizedItem] = multiprocessing.Manager().dict()
        self._pushed_items: dict[str, tuple[str, QueuePrioritizedItem]] = multiprocessing.Manager().dict()

    def get_queues(self) -> list[Queue]:
        time.sleep(self.sleep_time)
        return TypeAdapter(list[Queue]).validate_json(self.queue_response)

    def pop_item(self, queue: str) -> QueuePrioritizedItem | None:
        time.sleep(self.sleep_time)

        try:
            if WorkerManager.Queue.BOEFJES.value in queue:
                p_item = TypeAdapter(QueuePrioritizedItem).validate_json(self.boefje_responses.pop(0))
                self._popped_items[str(p_item.id)] = p_item
                self._tasks[str(p_item.id)] = self._task_from_id(p_item.id)
                return p_item

            if WorkerManager.Queue.NORMALIZERS.value in queue:
                p_item = TypeAdapter(QueuePrioritizedItem).validate_json(self.normalizer_responses.pop(0))
                self._popped_items[str(p_item.id)] = p_item
                return p_item
        except IndexError:
            raise self.raise_on_empty_queue

    def patch_task(self, task_id: UUID, status: TaskStatus) -> None:
        with self.log_path.open("a") as f:
            f.write(f"{task_id},{status.value}\n")

        task = self._task_from_id(task_id) if str(task_id) not in self._tasks else self._tasks[str(task_id)]
        task.status = status
        self._tasks[str(task_id)] = task

    def get_all_patched_tasks(self) -> list[tuple[str, ...]]:
        with self.log_path.open() as f:
            return [tuple(x.strip().split(",")) for x in f]

    def get_task(self, task_id: UUID) -> Task:
        return self._task_from_id(task_id) if str(task_id) not in self._tasks else self._tasks[str(task_id)]

    def _task_from_id(self, task_id: UUID):
        return Task(
            id=task_id,
            scheduler_id="test",
            type="test",
            p_item=self._popped_items[str(task_id)],
            status=TaskStatus.DISPATCHED,
            created_at=datetime.now(timezone.utc),
            modified_at=datetime.now(timezone.utc),
        )

    def push_item(self, queue_id: str, p_item: QueuePrioritizedItem) -> None:
        self._pushed_items[str(p_item.id)] = (queue_id, p_item)


class MockHandler(Handler):
    def __init__(self, exception=Exception):
        self.sleep_time = 0
        self.queue = Manager().Queue()
        self.exception = exception

    def handle(self, item: BoefjeMeta | NormalizerMeta):
        if str(item.id) == "9071c9fd-2b9f-440f-a524-ef1ca4824fd4":
            raise self.exception()

        time.sleep(self.sleep_time)
        self.queue.put(item)

    def get_all(self) -> list[BoefjeMeta | NormalizerMeta]:
        return [self.queue.get() for _ in range(self.queue.qsize())]


@pytest.fixture
def item_handler(tmp_path: Path):
    return MockHandler()


@pytest.fixture
def manager(item_handler: MockHandler, tmp_path: Path) -> SchedulerWorkerManager:
    scheduler_client = MockSchedulerClient(
        get_dummy_data("scheduler/queues_response.json"),
        2 * [get_dummy_data("scheduler/pop_response_boefje.json")] + [get_dummy_data("scheduler/should_crash.json")],
        [get_dummy_data("scheduler/pop_response_normalizer.json")],
        tmp_path / "patch_task_log",
    )

    return SchedulerWorkerManager(item_handler, scheduler_client, Settings(pool_size=1, poll_interval=0.01), "DEBUG")


@pytest.fixture
def api(tmp_path):
    from boefjes.api import app

    return TestClient(app)


@pytest.fixture
def octopoes_api_connector(request) -> OctopoesAPIConnector:
    test_node = f"test-{request.node.originalname}"

    connector = OctopoesAPIConnector(str(settings.octopoes_api), test_node)
    connector.create_node()
    yield connector
    connector.delete_node()


@pytest.fixture
def valid_time():
    return datetime.now(timezone.utc)


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
