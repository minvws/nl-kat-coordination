import json
import logging
import uuid
from typing import Optional

import pika
from celery import Celery
from pika.adapters.blocking_connection import BlockingChannel
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


class EventManager:
    def __init__(self, client: str, celery_app: Celery, celery_queue_name: str, channel: BlockingChannel):
        self.client = client
        self.celery_app = celery_app
        self.celery_queue_name = celery_queue_name
        self.channel = channel

        channel.queue_declare(queue=f"{client}__scan_profile_increments", durable=True)
        channel.queue_declare(queue=f"{client}__scan_profile_mutations", durable=True)

    def publish(self, event: DBEvent) -> None:
        event.client = self.client

        # schedule celery event processor
        self.celery_app.send_task(
            "octopoes.tasks.tasks.handle_event",
            (json.loads(event.json()),),
            queue=self.celery_queue_name,
            task_id=str(uuid.uuid4()),
        )

        logger.info(
            "Published handle_event task [operation_type=%s] [primary_key=%s] [client=%s]",
            event.operation_type,
            format_id_short(event.primary_key),
            event.client,
        )

        if isinstance(event, ScanProfileDBEvent):

            incremented = (event.operation_type == OperationType.CREATE and event.new_data.level > 0) or (
                event.operation_type == OperationType.UPDATE and event.new_data.level > event.old_data.level
            )
            if incremented:

                ooi = json.dumps(
                    {
                        "primary_key": event.new_data.reference,
                        "object_type": event.new_data.reference.class_,
                        "scan_profile": event.new_data.dict(),
                    }
                )

                self.channel.basic_publish(
                    "",
                    f"{event.client}__scan_profile_increments",
                    ooi.encode(),
                    properties=pika.BasicProperties(
                        delivery_mode=pika.DeliveryMode.Persistent,
                    ),
                )

                logger.info(
                    "Published scan_profile_increment [primary_key=%s] [level=%s]",
                    format_id_short(event.primary_key),
                    event.new_data.level,
                )

            # publish mutations
            mutation = ScanProfileMutation(
                operation=event.operation_type,
                primary_key=event.primary_key,
            )

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
                properties=pika.BasicProperties(
                    delivery_mode=pika.DeliveryMode.Persistent,
                ),
            )

            level = mutation.value.scan_profile.level if mutation.value != OperationType.DELETE else None
            logger.info(
                "Published scan profile mutation [operation_type=%s] [primary_key=%s] [level=%s]",
                mutation.operation,
                format_id_short(event.primary_key),
                level,
            )
