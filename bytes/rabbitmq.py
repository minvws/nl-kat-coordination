import pika

from bytes.config import Settings, settings
from bytes.events.events import Event
from bytes.events.manager import EventManager


class RabbitMQEventManager(EventManager):
    def __init__(self, settings: Settings):
        rabbit_connection = pika.BlockingConnection(pika.URLParameters(settings.queue_uri))
        self.channel = rabbit_connection.channel()

    def publish(self, event: Event) -> None:
        event_data = event.json()
        queue_name = self._queue_name(event)

        self.channel.queue_declare(queue_name)
        self.channel.basic_publish(
            "",
            queue_name,
            event_data.encode(),
        )

    @staticmethod
    def _queue_name(event: Event) -> str:
        return f"{event.organization}__raw_file_received"


class NullManager(EventManager):
    def publish(self, event: Event) -> None:
        pass


def create_event_manager() -> EventManager:
    if settings.queue_uri:
        return RabbitMQEventManager(settings)

    return NullManager()
