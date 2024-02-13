import functools
import socket
from concurrent import futures
from typing import Callable, Optional

import pika
import structlog
from retry import retry

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
        self.logger = structlog.getLogger(__name__)

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
        queue:
            A string defining the queue to listen to.
        durable:
            A boolean defining if the queue should be durable.
        prefetch_count:
            An integer defining the prefetch count.
        func:
            A callable that will be called when a message is received.
        executor:
            A concurrent.futures.ThreadPoolExecutor instance.
        connection:
            A pika.BlockingConnection instance.
        channel:
            A pika.BlockingConnection.channel instance.
    """

    def __init__(self, dsn: str, queue: str, func: Callable, durable: bool = True, prefetch_count: int = 1) -> None:
        """Initialize the RabbitMQ Listener

        Args:
            dsn:
                A string defining the data source name of the RabbitMQ host to
                connect to.
            queue:
                A string defining the queue to listen to.
            func:
                A callable that will be called when a message is received.
            durable:
                A boolean defining if the queue should be durable.
            prefetch_count:
                An integer defining the prefetch count.
        """
        super().__init__()

        self.dsn: str = dsn
        self.queue: str = queue
        self.durable: bool = durable
        self.prefetch_count: int = prefetch_count
        self.func: Callable = func

        self.executor: futures.ThreadPoolExecutor = futures.ThreadPoolExecutor(
            max_workers=10, thread_name_prefix=f"Listener-TPE-{self.__class__.__name__}"
        )
        self.connection: Optional[pika.BlockingConnection] = None
        self.channel: Optional[pika.BlockingConnection.channel] = None
        self.connect(self.queue, self.durable, self.prefetch_count)

    def listen(self) -> None:
        self.basic_consume(self.queue, self.durable, self.prefetch_count)

    @retry((pika.exceptions.AMQPConnectionError, socket.gaierror), delay=5, jitter=(1, 3), tries=5)
    def connect(self, queue: str, durable: bool, prefetch_count: int) -> None:
        """Connect to the RabbitMQ host and declare the queue."""
        try:
            self.connection = pika.BlockingConnection(pika.URLParameters(self.dsn))
        except pika.exceptions.AMQPConnectionError as exc:
            self.logger.error("AMQPConnectionError: %s", exc)
            raise exc

        try:
            self.channel = self.connection.channel()
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

    @retry(
        (pika.exceptions.AMQPConnectionError, pika.exceptions.ConnectionClosedByBroker), delay=5, jitter=(1, 3), tries=5
    )
    def basic_consume(self, queue: str, durable: bool, prefetch_count: int) -> None:
        if self.connection and self.connection.is_closed:
            self.connect(queue, durable, prefetch_count)

        if not self.channel:
            raise RuntimeError("No channel available to consume messages on!")

        if not self.connection:
            raise RuntimeError("No connection available to consume messages on!")

        try:
            self.channel.basic_qos(prefetch_count=prefetch_count)
            self.channel.basic_consume(queue, on_message_callback=self.callback)
            self.channel.start_consuming()
        except pika.exceptions.AMQPChannelError as exc:
            # Do not recover on channel errors
            self.logger.error("AMQPChannelError: %s", exc)
            raise exc

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
        self.logger.debug(
            "Received message on queue %s", method.routing_key, routing_key=method.routing_key, message=body
        )

        # Submit the message to the thread pool executor
        self.executor.submit(self.dispatch, channel, method.delivery_tag, body)

    def dispatch(self, channel, delivery_tag, body: bytes) -> None:
        # Check if we still have a connection
        if not self.connection:
            self.logger.debug("No connection available, cannot dispatch message!")
            return

        # Check if we still have a channel
        if not self.channel:
            self.logger.debug("No channel available, cannot dispatch message!")
            return

        # Call the function
        self.func(body)

        # Acknowledge the message
        self.connection.add_callback_threadsafe(functools.partial(self.ack_message, channel, delivery_tag))

    def ack_message(self, channel, delivery_tag):
        if channel.is_open:
            channel.basic_ack(delivery_tag)
        else:
            # Channel is already closed, so we can't ack this message
            self.logger.debug("Channel already closed, cannot ack message!")

    def stop(self) -> None:
        self.logger.debug("Stopping RabbitMQ connection")

        self.executor.shutdown(wait=True)

        if self.connection:
            self.connection.add_callback_threadsafe(self._close_callback)

        self.logger.debug("RabbitMQ connection closed")

    def _close_callback(self):
        self.channel.stop_consuming()
        self.channel.close()
        self.connection.close()
