import logging
from functools import lru_cache

import pika
import pika.exceptions

from bytes.config import Settings, settings
from bytes.events.events import Event
from bytes.events.manager import EventManager


logger = logging.getLogger(__name__)


class RabbitMQEventManager(EventManager):
    def __init__(self, settings: Settings):
        self.queue_uri = settings.queue_uri
        self.connection = self.connect()

    def publish(self, event: Event) -> None:
        event_data = event.json()
        queue_name = self._queue_name(event)

        logger.info(f"Publishing {event._event_id} event to {queue_name}")
        logger.debug(f"Event: {event_data}")

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
        connection = self.get_rabbitmq_connection()

        if connection.is_closed:
            self.get_rabbitmq_connection.cache_clear()
            connection = self.get_rabbitmq_connection()

        return connection

    @lru_cache(maxsize=None)
    def get_rabbitmq_connection(self) -> pika.BlockingConnection:
        logger.info(f"Connecting to RabbitMQ")

        return pika.BlockingConnection(pika.URLParameters(settings.queue_uri))

    @staticmethod
    def _queue_name(event: Event) -> str:
        return f"{event.organization}__{event._event_id}"


class NullManager(EventManager):
    def publish(self, event: Event) -> None:
        pass


def create_event_manager() -> EventManager:
    if settings.queue_uri:
        return RabbitMQEventManager(settings)

    return NullManager()
