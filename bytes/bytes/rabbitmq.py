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
        self._check_connection()

        event_data = event.json()
        logger.debug("Publishing event: %s", event_data)
        queue_name = self._queue_name(event)

        try:
            self.channel.queue_declare(queue_name, durable=True)
        except pika.exceptions.AMQPError as e:
            logger.info("Channel error %s, recreating channel", e)
            self._check_connection()
            self.channel.queue_declare(queue_name, durable=True)

        try:
            self.channel.basic_publish("", queue_name, event_data.encode())
        except pika.exceptions.AMQPError:
            logger.info("RabbitMQ connection was closed: retrying with a new connection.")
            self._check_connection()
            self.channel.basic_publish("", queue_name, event_data.encode())

        logger.info("Published event [event_id=%s] to queue %s", event.event_id, queue_name)

    def _check_connection(self):
        if self.connection.is_closed:
            self.connection = pika.BlockingConnection(pika.URLParameters(self.queue_uri))
            self.channel = self.connection.channel()
            logger.warning("Reconnected to RabbitMQ because connection was closed")

        if self.channel.is_closed:
            self.channel = self.connection.channel()
            logger.warning("Recreated RabbitMQ channel because channel was closed")

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
        return RabbitMQEventManager(str(settings.queue_uri))

    return NullManager()
