import json
import logging
import uuid
from typing import cast

import pika
from celery import Celery
from pika.adapters.blocking_connection import BlockingChannel

from octopoes.events.events import DBEvent, OOIDBEvent, OperationType, ScanProfileDBEvent


logger = logging.getLogger(__name__)


class EventManager:
    def __init__(self, client: str, celery_app: Celery, celery_queue_name: str, channel: BlockingChannel):
        self.client = client
        self.celery_app = celery_app
        self.celery_queue_name = celery_queue_name
        self.channel = channel

        channel.queue_declare(queue=f"{client}__scan_profile_increments", durable=True)

    def publish(self, event: DBEvent) -> None:
        logger.info("Publishing event %s", event.json())

        event.client = self.client

        # schedule celery event processor
        self.celery_app.send_task(
            "octopoes.tasks.tasks.handle_event",
            (json.loads(event.json()),),
            queue=self.celery_queue_name,
            task_id=str(uuid.uuid4()),
        )

        # publish increased scan-level to scheduler
        if (
            isinstance(event, ScanProfileDBEvent)
            and event.operation_type == OperationType.UPDATE
            and event.new_data.level > event.old_data.level
        ):
            event_data = json.dumps(
                {
                    "reference": event.new_data.reference,
                    "ooi_type": event.new_data.reference.class_,
                    "level": event.new_data.level,
                }
            )
            logger.info("Publishing ScanProfileDBEvent to RabbitMQ: %s", event_data)

            self.channel.basic_publish(
                "",
                f"{event.client}__scan_profile_increments",
                event_data.encode(),
                properties=pika.BasicProperties(
                    delivery_mode=pika.DeliveryMode.Persistent,
                ),
            )

        # notify rocky
        if event.entity_type == "ooi" and event.operation_type == OperationType.CREATE:
            event = cast(OOIDBEvent, event)
            logger.info("Publishing OOIDBEvent for Rocky: %s", event.json())

            self.channel.basic_publish(
                "",
                "create_events",
                json.dumps({"reference": str(event.new_data.reference), "organization": event.client}).encode(),
                properties=pika.BasicProperties(
                    delivery_mode=pika.DeliveryMode.Persistent,
                ),
            )
