import json
import logging
import urllib.parse
from typing import Dict, Optional

import pika

from ..connector import Connector  # noqa: TID252


class Listener(Connector):
    """The Listener base class interface

    Attributes:
        name:
            Identifier of the Listener
        logger:
            The logger for the class.
    """

    name: Optional[str] = None

    def __init__(self) -> None:
        super().__init__()
        self.logger = logging.getLogger(__name__)

    def listen(self) -> None:
        raise NotImplementedError

    def stop(self) -> None:
        raise NotImplementedError


class RabbitMQ(Listener):
    """A RabbitMQ Listener implementation that allows subclassing of specific
    RabbitMQ channel listeners. You can subclass this class and set the
    channel and procedure that needs to be dispatched when receiving messages
    from a RabbitMQ queue.

    Attributes:
        dsn:
            A string defining the data source name of the RabbitMQ host to
            connect to.
        connection:
            A pika.BlockingConnection instance.
        channel:
            A pika.BlockingConnection.channel instance.
    """

    def __init__(self, dsn: str):
        """Initialize the RabbitMQ Listener

        Args:
            dsn:
                A string defining the data source name of the RabbitMQ host to
                connect to.
        """
        super().__init__()
        self.dsn = dsn

        self.connection = pika.BlockingConnection(pika.URLParameters(self.dsn))
        self.channel = self.connection.channel()

    def dispatch(self, body: bytes) -> None:
        """Dispatch a message without a return value"""
        raise NotImplementedError

    def basic_consume(self, queue: str, durable: bool, prefetch_count: int) -> None:
        try:
            self.channel.queue_declare(queue=queue, durable=durable)
        except pika.exceptions.ChannelClosedByBroker as exc:
            if "inequivalent arg 'durable'" in exc.reply_text:
                # Queue changed from non-durable to durable. Given that
                # previously they weren't durable and contents would also be
                # lost if RabbitMQ restarted, we will just delete the queue and
                # recreate it to provide for a smooth upgrade.
                self.channel = self.connection.channel()
                self.channel.queue_delete(queue=queue)
                self.channel.queue_declare(queue=queue, durable=durable)
            else:
                raise
        self.channel.basic_qos(prefetch_count=prefetch_count)
        self.channel.basic_consume(queue, on_message_callback=self.callback)
        self.channel.start_consuming()

    def get(self, queue: str) -> Optional[Dict[str, object]]:
        method, properties, body = self.channel.basic_get(queue)

        if body is None:
            return None

        response = json.loads(body)
        self.channel.basic_ack(method.delivery_tag)

        return response

    def callback(
        self,
        channel: pika.channel.Channel,
        method: pika.spec.Basic.Deliver,
        properties: pika.spec.BasicProperties,
        body: bytes,
    ) -> None:
        """Callback function that is called when a message is received on the
        queue.
        """
        self.logger.debug("Received message on queue %s, message: %r", method.routing_key, body)

        self.dispatch(body)

        channel.basic_ack(method.delivery_tag)

    def is_healthy(self) -> bool:
        """Check if the RabbitMQ connection is healthy"""
        parsed_url = urllib.parse.urlparse(self.dsn)
        if parsed_url.hostname is None or parsed_url.port is None:
            self.logger.warning(
                "Not able to parse hostname and port from %s [host=%s]",
                self.dsn,
                self.dsn,
            )
            return False

        return self.is_host_available(parsed_url.hostname, parsed_url.port)

    def stop(self) -> None:
        self.logger.debug("Stopping RabbitMQ connection")

        self.connection.add_callback_threadsafe(self._close_callback)

        self.logger.debug("RabbitMQ connection closed")

    def _close_callback(self):
        self.channel.stop_consuming()
        self.channel.close()
        self.connection.close()
