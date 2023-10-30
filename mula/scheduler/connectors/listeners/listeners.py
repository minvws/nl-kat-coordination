import json
import logging
import urllib.parse
from concurrent import futures
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

    To combat potential dropping of AMQP/stream connections due to AMQP heartbeat
    timeouts, due to long running tasks, we will delegate processing of the
    incoming message to another thread, while the connection adapter’s thread
    continues to service its I/O loop’s message pump, permitting AMQP heartbeats
    and other I/O to be serviced in a timely fashion.

    Source: https://pika.readthedocs.io/en/stable/modules/adapters/index.html#requesting-message-acknowledgements-from-another-thread

    Attributes:
        dsn:
            A string defining the data source name of the RabbitMQ host to
            connect to.
        connection:
            A pika.BlockingConnection instance.
        channel:
            A pika.BlockingConnection.channel instance.
        executor:
            A concurrent.futures.ThreadPoolExecutor instance.
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
        self.executor: futures.ThreadPoolExecutor = futures.ThreadPoolExecutor(max_workers=10)

    def dispatch(self, channel, delivery_tag, body: bytes) -> None:
        """Dispatch a message without a return value"""
        raise NotImplementedError

    def basic_consume(self, queue: str, durable: bool, prefetch_count: int) -> None:
        while True:
            self.connection = pika.BlockingConnection(pika.URLParameters(self.dsn))
            self.channel = self.connection.channel()

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

            try:
                self.channel.basic_qos(prefetch_count=prefetch_count)
                self.channel.basic_consume(queue, on_message_callback=self.callback)
                self.channel.start_consuming()
            except pika.exceptions.ConnectionClosedByBroker:
                # Recover from server-initiated connection closure, this also
                # includes when node is stopped cleanly
                continue
            except pika.exceptions.AMQPChannelError as exc:
                # Do not recover on channel errors
                self.logger.error("AMQPChannelError: %s", exc)
                raise exc
            except pika.exceptions.AMQPConnectionError as exc:
                # Recover on all other connection errors
                self.logger.warning("RabbitMQ connection was closed, re-establishing connection: %s", exc)
                continue

    def get(self, queue: str) -> Optional[Dict[str, object]]:
        method, properties, body = self.channel.basic_get(queue)

        if body is None:
            return None

        response = json.loads(body)
        self.channel.basic_ack(method.delivery_tag)

        return response

    def ack_message(self, channel, delivery_tag):
        if channel.is_open:
            channel.basic_ack(delivery_tag)
        else:
            # Channel is already closed, so we can't ack this message
            self.logger.debug("Channel already closed, cannot ack message!")

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
        self.executor.submit(self.dispatch, channel, method.delivery_tag, body)

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
        self.executor.shutdown()

        self.logger.debug("RabbitMQ connection closed")

    def _close_callback(self):
        self.channel.stop_consuming()
        self.channel.close()
        self.connection.close()
