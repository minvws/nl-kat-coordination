import json
import logging
import threading
import uuid
from typing import Callable, Optional

import pika
from celery import Celery
from pika.adapters.blocking_connection import BlockingChannel
from pika.exceptions import StreamLostError
from pydantic import BaseModel

from octopoes.events.events import DBEvent, OperationType, ScanProfileDBEvent
from octopoes.models import ScanProfile, format_id_short

logger = logging.getLogger(__name__)


class AbstractOOI(BaseModel):
    primary_key: str
    object_type: str
    scan_profile: ScanProfile


class ScanProfileMutation(BaseModel):
    operation: OperationType
    primary_key: str
    value: Optional[AbstractOOI]


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
    ):
        self.client = client
        self.queue_uri = queue_uri
        self.celery_app = celery_app
        self.celery_queue_name = celery_queue_name
        self.channel_factory = channel_factory

        self._try_connect()

    def publish(self, event: DBEvent) -> None:
        try:
            self._publish(event)
        except StreamLostError:  # Retry publishing once on connection issues
            logger.exception("Failed publishing event, retrying...")

            try:
                self._connect()
                self._publish(event)
            except StreamLostError:
                logger.exception("Failed publishing event again")
                raise

    def _publish(self, event: DBEvent) -> None:
        event.client = self.client

        # schedule celery event processor
        self.celery_app.send_task(
            "octopoes.tasks.tasks.handle_event",
            (json.loads(event.json()),),
            queue=self.celery_queue_name,
            task_id=str(uuid.uuid4()),
        )

        logger.debug(
            "Published handle_event task [operation_type=%s] [primary_key=%s] [client=%s]",
            event.operation_type,
            format_id_short(event.primary_key),
            event.client,
        )

        if not isinstance(event, ScanProfileDBEvent):
            return

        incremented = (event.operation_type == OperationType.CREATE and event.new_data.level > 0) or (
            event.operation_type == OperationType.UPDATE
            and event.old_data
            and event.new_data.level > event.old_data.level
        )

        if incremented:
            ooi = json.dumps(
                {
                    "primary_key": event.reference,
                    "object_type": event.reference.class_,
                    "scan_profile": event.new_data.dict(),
                }
            )

            self.channel.basic_publish(
                "",
                f"{event.client}__scan_profile_increments",
                ooi.encode(),
                properties=pika.BasicProperties(delivery_mode=pika.DeliveryMode.Persistent),
            )

            logger.debug(
                "Published scan_profile_increment [primary_key=%s] [level=%s]",
                format_id_short(event.primary_key),
                event.new_data.level,
            )

        # publish mutations
        mutation = ScanProfileMutation(operation=event.operation_type, primary_key=event.primary_key)

        if event.operation_type != OperationType.DELETE:
            mutation.value = AbstractOOI(
                primary_key=event.new_data.reference,
                object_type=event.new_data.reference.class_,
                scan_profile=event.new_data,
            )

        self.channel.basic_publish(
            "",
            f"{event.client}__scan_profile_mutations",
            mutation.json().encode(),
            properties=pika.BasicProperties(delivery_mode=pika.DeliveryMode.Persistent),
        )

        level = mutation.value.scan_profile.level if mutation.value is not None else None
        logger.debug(
            "Published scan profile mutation [operation_type=%s] [primary_key=%s] [level=%s]",
            mutation.operation,
            format_id_short(event.primary_key),
            level,
        )

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

    def _connect(self) -> None:
        self.channel = self.channel_factory(self.queue_uri)
        self.channel.queue_declare(queue=f"{self.client}__scan_profile_increments", durable=True)
        self.channel.queue_declare(queue=f"{self.client}__scan_profile_mutations", durable=True)
