import threading
import time
import unittest
from unittest import mock

import pika

from scheduler import connectors, utils
from tests.mocks import listener


class RabbitMQTestCase(unittest.TestCase):
    def setUp(self):
        self.listeners: list[connectors.listeners.Listener] = []

        threading.excepthook = self.unhandled_exception

    def tearDown(self):
        for l in self.listeners:
            l.stop()

    def unhandled_exception(self, args: threading.ExceptHookArgs) -> None:
        breakpoint()
        for l in self.listeners:
            l.stop()

    def test_shutdown(self):
        def test_func(body):
            pass

        stop_event = threading.Event()

        lst = listener.MockRabbitMQ(
            dsn="amqp://guest:guest@ci_rabbitmq:5672/%2Fkat",
            queue="test",
            func=test_func,
        )
        self.listeners.append(lst)

        # Run the listener
        t = utils.ThreadRunner(
            name="MockRabbitMQ",
            target=lst.listen,
            stop_event=stop_event,
            interval=0.01,
            daemon=False,
            loop=False,
        )
        t.start()

        # Make sure the listener is running
        self.assertTrue(t.is_alive())

        breakpoint()

        # Stop the listener
        lst.channel.stop_consuming()
        lst.channel.close()
        lst.connection.close()

        # Call stop on the listener
        lst.stop()

        # Make sure the listener is stopped
        self.assertFalse(t.is_alive())

    @mock.patch("pika.adapters.blocking_connection.BlockingChannel.start_consuming")
    def test_start_consuming_exception(self, mock_start_consuming):
        def test_func(body):
            pass

        stop_event = threading.Event()

        lst = listener.MockRabbitMQ(
            dsn="amqp://guest:guest@ci_rabbitmq:5672/%2Fkat",
            queue="test",
            func=test_func,
        )
        self.listeners.append(lst)

        # Mocks
        # This will issue an unhandled_exception
        mock_start_consuming.side_effect = Exception("Test Exception")

        # Run the listener
        t = utils.ThreadRunner(
            name="MockRabbitMQ",
            target=lst.listen,
            stop_event=stop_event,
            interval=0.01,
            daemon=False,
            loop=False,
        )
        t.start()

        while t.is_alive():
            time.sleep(0.1)

        # Make sure the listener stopped running
        for t in threading.enumerate():
            if t is threading.main_thread():
                continue

            self.assertFalse(t.is_alive())

    def test_exception(self):
        def test_func(body):
            raise Exception("Test Exception")

        stop_event = threading.Event()

        lst = listener.MockRabbitMQ(
            dsn="amqp://guest:guest@ci_rabbitmq:5672/%2Fkat",
            queue="test",
            func=test_func,
        )
        self.listeners.append(lst)

        # Run the listener
        t = utils.ThreadRunner(
            name="MockRabbitMQ",
            target=lst.listen,
            stop_event=stop_event,
            interval=0.01,
            daemon=False,
            loop=False,
        )
        t.start()

        # Make sure the listener is running
        self.assertTrue(t.is_alive())

        # Act: send a message
        connection = pika.BlockingConnection(
            pika.URLParameters("amqp://guest:guest@ci_rabbitmq:5672/%2Fkat")
        )
        channel = connection.channel()
        channel.queue_declare(queue="test", durable=True)
        channel.basic_publish(
            exchange="",
            routing_key="test",
            body="Test Message",
        )
        channel.stop_consuming()
        channel.close()
        connection.close()

        for t in threading.enumerate():
            if t is threading.main_thread():
                continue

            self.assertFalse(t.is_alive())

        # Stop the listener
        lst.stop()
