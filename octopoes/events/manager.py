import json
import uuid

import structlog
from celery import Celery

from octopoes.events.events import DBEvent
from octopoes.models import format_id_short

logger = structlog.get_logger(__name__)


class EventManager:
    def __init__(self, client: str, celery_app: Celery, celery_queue_name: str):
        self.client = client
        self.celery_app = celery_app
        self.celery_queue_name = celery_queue_name

    def publish_now(self, event: DBEvent, session):
        from octopoes.core.app import bootstrap_octopoes

        bootstrap_octopoes(event.client, session).process_event(event)

    def publish(self, event: DBEvent) -> None:
        self._publish(event)

    def _publish(self, event: DBEvent) -> None:
        # schedule celery event processor
        self.celery_app.send_task(
            "openkat.tasks.handle_event",
            (json.loads(event.model_dump_json()),),
            queue=self.celery_queue_name,
            task_id=str(uuid.uuid4()),
        )

        logger.debug(
            "Published handle_event task [operation_type=%s] [primary_key=%s] [client=%s]",
            event.operation_type,
            format_id_short(event.primary_key),
            event.client,
        )
