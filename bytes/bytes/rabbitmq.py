import logging
from functools import lru_cache

import pika
import pika.exceptions

from bytes.config import get_settings
from bytes.events.events import Event
from bytes.events.manager import EventManager

logger = logging.getLogger(__name__)


class RabbitMQEventManager(EventManager):
    def __init__(self, queue_uri: str):
        self.queue_uri = queue_uri
        self.connection = get_connection(self.queue_uri)
        self.channel = self.connection.channel()

    def publish(self, event: Event) -> None:
        event_data = event.json()
        queue_name = self._queue_name(event)

        logger.debug("Publishing event: %s", event_data)
        self.channel.queue_declare(queue_name)

        try:
            self.channel.basic_publish("", queue_name, event_data.encode())
        except pika.exceptions.ConnectionClosed:
            logger.exception("RabbitMQ connection was closed: retrying with a new connection.")

            get_connection.cache_clear()
            self.connection = get_connection(self.queue_uri)
            self.channel = self.connection.channel()

            self.channel.basic_publish("", queue_name, event_data.encode())

        logger.info("Published event [event_id=%s] to queue %s", event.event_id, queue_name)

    @staticmethod
    def _queue_name(event: Event) -> str:
        return f"{event.organization}__{event.event_id}"


class NullManager(EventManager):
    def publish(self, event: Event) -> None:
        pass


@lru_cache(maxsize=1)
def get_connection(queue_uri: str) -> pika.BlockingConnection:
    logger.info("Connecting to RabbitMQ")
    connection = pika.BlockingConnection(pika.URLParameters(queue_uri))
    logger.info("Connected to RabbitMQ")

    return connection


def create_event_manager() -> EventManager:
    settings = get_settings()

    if settings.queue_uri:
        return RabbitMQEventManager(settings.queue_uri)

    return NullManager()
