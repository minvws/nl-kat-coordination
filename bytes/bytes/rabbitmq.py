import logging
from functools import cached_property

import pika
import pika.exceptions

from bytes.config import get_settings
from bytes.events.events import Event
from bytes.events.manager import EventManager

logger = logging.getLogger(__name__)


class RabbitMQEventManager(EventManager):
    def __init__(self, queue_uri: str):
        self.queue_uri = queue_uri
        self.connection = self.connect()

    def publish(self, event: Event) -> None:
        event_data = event.json()
        queue_name = self._queue_name(event)

        logger.info("Publishing %s event to %s", event.event_id, queue_name)
        logger.debug("Event: %s", event_data)

        channel = self.connection.channel()
        channel.queue_declare(queue_name)

        try:
            channel.basic_publish(
                "",
                queue_name,
                event_data.encode(),
            )
        except pika.exceptions.ConnectionClosed:
            logger.exception("RabbitMQ connection was closed: retrying")
            self.connect()
            channel.basic_publish(
                "",
                queue_name,
                event_data.encode(),
            )

    def connect(self) -> pika.BlockingConnection:
        connection = self.get_rabbitmq_connection

        if connection.is_closed:
            del self.get_rabbitmq_connection
            connection = self.get_rabbitmq_connection

        return connection

    @cached_property
    def get_rabbitmq_connection(self) -> pika.BlockingConnection:
        logger.info("Connecting to RabbitMQ")

        return pika.BlockingConnection(pika.URLParameters(self.queue_uri))

    @staticmethod
    def _queue_name(event: Event) -> str:
        return f"{event.organization}__{event.event_id}"


class NullManager(EventManager):
    def publish(self, event: Event) -> None:
        pass


def create_event_manager() -> EventManager:
    settings = get_settings()

    if settings.queue_uri:
        return RabbitMQEventManager(settings.queue_uri)

    return NullManager()
