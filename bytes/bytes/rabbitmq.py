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
        self.connection = pika.BlockingConnection(pika.URLParameters(self.queue_uri))
        self.channel = self.connection.channel()
        logger.info("Connected to RabbitMQ")

    def publish(self, event: Event) -> None:
        event_data = event.json()
        queue_name = self._queue_name(event)

        logger.debug("Publishing event: %s", event_data)
        try:
            self.channel.queue_declare(queue_name, durable=True)
        except pika.exceptions.AMQPChannelError as e:
            logger.info("Channel error %s, recreating channel", e)
            self.channel = self.connection.channel()
            self.channel.queue_declare(queue_name, durable=True)

        try:
            self.channel.basic_publish("", queue_name, event_data.encode())
        except pika.exceptions.ConnectionClosed:
            logger.exception("RabbitMQ connection was closed: retrying with a new connection.")

            self.connection = pika.BlockingConnection(pika.URLParameters(self.queue_uri))
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
def create_event_manager() -> EventManager:
    settings = get_settings()

    if settings.queue_uri:
        return RabbitMQEventManager(settings.queue_uri)

    return NullManager()
