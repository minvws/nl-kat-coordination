import json
import threading
import time
import uuid
from collections.abc import Callable

import pika
import structlog
from celery import Celery
from pika.adapters.blocking_connection import BlockingChannel
from pika.exceptions import StreamLostError
from pydantic import BaseModel

from octopoes.events.events import DBEvent, OperationType, ScanProfileDBEvent
from octopoes.models import ScanProfile

logger = structlog.get_logger(__name__)


class AbstractOOI(BaseModel):
    primary_key: str
    object_type: str
    scan_profile: ScanProfile


class ScanProfileMutation(BaseModel):
    operation: OperationType
    primary_key: str
    value: AbstractOOI | None = None
    client_id: str


thread_local = threading.local()


def get_rabbit_channel(queue_uri: str) -> BlockingChannel:
    try:
        if thread_local.rabbit_channel.is_closed or thread_local.rabbit_channel.connection.is_closed:
            raise ConnectionError("RabbitMQ channel is closed, establishing a new connection...")

        return thread_local.rabbit_channel
    except (AttributeError, ConnectionError, StreamLostError):
        connection = pika.BlockingConnection(pika.URLParameters(queue_uri))
        logger.info("Connected to RabbitMQ")

        thread_local.rabbit_channel = connection.channel()
        thread_local.rabbit_channel.queue_declare(queue="create_events", durable=True)

        return thread_local.rabbit_channel


class EventManager:
    def __init__(
        self,
        client: str,
        queue_uri: str,
        celery_app: Celery,
        celery_queue_name: str,
        channel_factory: Callable[[str], BlockingChannel] = get_rabbit_channel,
        batch_size: int = 100,
        flush_interval: float = 5.0,
    ):
        self.client = client
        self.queue_uri = queue_uri
        self.celery_app = celery_app
        self.celery_queue_name = celery_queue_name
        self.channel_factory = channel_factory
        self.batch_size = batch_size
        self.flush_interval = flush_interval

        # Batch processing attributes
        self._event_batch: list[DBEvent] = []
        self._scan_profile_mutations: list[ScanProfileMutation] = []
        self._batch_lock = threading.RLock()
        self._last_flush_time = time.time()
        self._flush_timer: threading.Timer | None = None

        self._try_connect()
        self._start_flush_timer()

    def publish(self, event: DBEvent) -> None:
        with self._batch_lock:
            # Add event to batch
            self._event_batch.append(event)

            # If it's a scan profile event, prepare the mutation
            if isinstance(event, ScanProfileDBEvent):
                mutation = self._create_scan_profile_mutation(event)
                if mutation:
                    self._scan_profile_mutations.append(mutation)

            # Check if we need to flush the batch
            if len(self._event_batch) >= self.batch_size or time.time() - self._last_flush_time >= self.flush_interval:
                self._flush_batch()

    def _create_scan_profile_mutation(self, event: ScanProfileDBEvent) -> ScanProfileMutation | None:
        """Create a scan profile mutation from an event"""
        mutation = ScanProfileMutation(
            operation=event.operation_type, primary_key=event.primary_key, client_id=event.client
        )

        if event.operation_type != OperationType.DELETE and event.new_data is not None:
            mutation.value = AbstractOOI(
                primary_key=event.new_data.reference,
                object_type=event.new_data.reference.class_,
                scan_profile=event.new_data,
            )

        return mutation

    def _flush_batch(self) -> None:
        """Flush the current batch of events to RabbitMQ"""
        if not self._event_batch:
            return

        try:
            self._publish_batch()
        except StreamLostError:  # Retry publishing once on connection issues
            logger.exception("Failed publishing event batch, retrying...")

            try:
                self._connect()
                self._publish_batch()
            except StreamLostError:
                logger.exception("Failed publishing event batch again")
                raise
        finally:
            self._last_flush_time = time.time()

    def _publish_batch(self) -> None:
        """Publish the current batch of events"""
        if not self._event_batch:
            return

        # Make a local copy of the batch and clear the main batch
        with self._batch_lock:
            events_to_publish = self._event_batch.copy()
            scan_profile_mutations = self._scan_profile_mutations.copy()
            self._event_batch = []
            self._scan_profile_mutations = []

        # Publish events in batch
        batch_size = len(events_to_publish)
        if batch_size > 0:
            # Group events by type for more efficient processing
            grouped_events: dict[str, list[DBEvent]] = {}
            for event in events_to_publish:
                event_type = event.entity_type
                if event_type not in grouped_events:
                    grouped_events[event_type] = []
                grouped_events[event_type].append(event)

            # Send each group as a batch task
            for event_type, events in grouped_events.items():
                self.celery_app.send_task(
                    "octopoes.tasks.tasks.handle_event_batch",
                    (json.loads(json.dumps([event.model_dump() for event in events]))),
                    queue=self.celery_queue_name,
                    task_id=str(uuid.uuid4()),
                )

                logger.debug("Published batch of %d %s events", len(events), event_type)

        # Publish scan profile mutations in batch
        if scan_profile_mutations:
            mutations_json = [mutation.model_dump_json().encode() for mutation in scan_profile_mutations]

            for mutation_json in mutations_json:
                self.channel.basic_publish(
                    "",
                    "scan_profile_mutations",
                    mutation_json,
                    properties=pika.BasicProperties(delivery_mode=pika.DeliveryMode.Persistent),
                )

            logger.debug("Published %d scan profile mutations", len(scan_profile_mutations))

    def _start_flush_timer(self) -> None:
        """Start a timer to periodically flush the event batch"""

        def _timer_callback():
            with self._batch_lock:
                if self._event_batch:
                    self._flush_batch()
            self._start_flush_timer()

        self._flush_timer = threading.Timer(self.flush_interval, _timer_callback)
        self._flush_timer.daemon = True
        self._flush_timer.start()

    def _try_connect(self):
        try:
            self._connect()
        except StreamLostError:  # Retry connecting once on connection issues
            logger.exception("Failed connecting to rabbitmq, retrying...")

            try:
                self._connect()
            except StreamLostError:
                logger.exception("Failed connecting to rabbitmq again")
                raise

    def force_flush(self) -> None:
        """Force flush any pending events"""
        with self._batch_lock:
            self._flush_batch()

    def _connect(self) -> None:
        self.channel = self.channel_factory(self.queue_uri)
        self.channel.queue_declare(queue="scan_profile_mutations", durable=True)
