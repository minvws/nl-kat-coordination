import json
import uuid
from datetime import datetime
from unittest.mock import Mock

from octopoes.events.events import OOIDBEvent, OperationType, ScanProfileDBEvent
from octopoes.events.manager import EventManager


def test_event_manager_batch_collection(mocker, network):
    """Test that events are collected in a batch and not immediately sent."""
    celery_mock = mocker.Mock()
    channel_mock = mocker.Mock()

    # Create event manager with batch size of 3
    manager = EventManager(
        "test", "amqp://test-queue-uri", celery_mock, "queue", lambda x: channel_mock, batch_size=3, flush_interval=10.0
    )

    # Create and publish two events (less than batch size)
    event1 = OOIDBEvent(
        operation_type=OperationType.CREATE, valid_time=datetime(2023, 1, 1), new_data=network, client="test"
    )
    event2 = OOIDBEvent(
        operation_type=OperationType.UPDATE, valid_time=datetime(2023, 1, 1), new_data=network, client="test"
    )

    manager.publish(event1)
    manager.publish(event2)

    # Verify that no events have been sent yet (batch size not reached)
    celery_mock.send_task.assert_not_called()
    channel_mock.basic_publish.assert_not_called()


def test_event_manager_batch_flush_on_size(mocker, network):
    """Test that events are flushed when batch size is reached."""
    celery_mock = mocker.Mock()
    channel_mock = mocker.Mock()

    # Mock UUID to get predictable task IDs
    mocker.patch.object(uuid, "uuid4", return_value="1754a4c8-f0b8-42c8-b294-5706ce23a47d")

    # Create event manager with batch size of 2
    manager = EventManager(
        "test", "amqp://test-queue-uri", celery_mock, "queue", lambda x: channel_mock, batch_size=2, flush_interval=10.0
    )

    # Create and publish two events (equal to batch size)
    event1 = OOIDBEvent(
        operation_type=OperationType.CREATE, valid_time=datetime(2023, 1, 1), new_data=network, client="test"
    )
    event2 = OOIDBEvent(
        operation_type=OperationType.UPDATE, valid_time=datetime(2023, 1, 1), new_data=network, client="test"
    )

    manager.publish(event1)
    manager.publish(event2)

    # Verify that events have been sent as a batch
    celery_mock.send_task.assert_called_once()
    assert celery_mock.send_task.call_args[0][0] == "octopoes.tasks.tasks.handle_event_batch"

    # Check that the batch contains both events
    events_batch = json.loads(json.dumps(celery_mock.send_task.call_args[0][1][0]))
    assert len(events_batch) == 2
    assert events_batch[0]["operation_type"] == "create"
    assert events_batch[1]["operation_type"] == "update"


def test_event_manager_batch_flush_on_interval(mocker, network):
    """Test that events are flushed when the flush interval is reached."""
    celery_mock = mocker.Mock()
    channel_mock = mocker.Mock()

    # Mock time.time to control the timer
    mock_time = Mock()
    mock_time.side_effect = [100.0, 100.0, 106.0]  # Initial, first check, second check (after interval)
    mocker.patch("time.time", mock_time)

    # Mock the timer to immediately call the callback
    mock_timer = Mock()
    mocker.patch("threading.Timer", return_value=mock_timer)

    # Create event manager with batch size of 10 (larger than we'll use) and flush interval of 5
    manager = EventManager(
        "test", "amqp://test-queue-uri", celery_mock, "queue", lambda x: channel_mock, batch_size=10, flush_interval=5.0
    )

    # Create and publish one event (less than batch size)
    event = OOIDBEvent(
        operation_type=OperationType.CREATE, valid_time=datetime(2023, 1, 1), new_data=network, client="test"
    )

    manager.publish(event)

    # Verify that no events have been sent yet
    celery_mock.send_task.assert_not_called()

    # Simulate timer callback
    manager._flush_batch()

    # Verify that the event has been sent
    celery_mock.send_task.assert_called_once()
    assert celery_mock.send_task.call_args[0][0] == "octopoes.tasks.tasks.handle_event_batch"


def test_event_manager_force_flush(mocker, network):
    """Test that events are flushed when force_flush is called."""
    celery_mock = mocker.Mock()
    channel_mock = mocker.Mock()

    # Create event manager with large batch size and interval
    manager = EventManager(
        "test",
        "amqp://test-queue-uri",
        celery_mock,
        "queue",
        lambda x: channel_mock,
        batch_size=100,
        flush_interval=60.0,
    )

    # Create and publish one event (less than batch size)
    event = OOIDBEvent(
        operation_type=OperationType.CREATE, valid_time=datetime(2023, 1, 1), new_data=network, client="test"
    )

    manager.publish(event)

    # Verify that no events have been sent yet
    celery_mock.send_task.assert_not_called()

    # Force flush
    manager.force_flush()

    # Verify that the event has been sent
    celery_mock.send_task.assert_called_once()
    assert celery_mock.send_task.call_args[0][0] == "octopoes.tasks.tasks.handle_event_batch"


def test_event_manager_batch_scan_profile_mutations(mocker, empty_scan_profile):
    """Test that scan profile mutations are batched correctly."""
    celery_mock = mocker.Mock()
    channel_mock = mocker.Mock()

    # Create event manager with batch size of 2
    manager = EventManager(
        "test", "amqp://test-queue-uri", celery_mock, "queue", lambda x: channel_mock, batch_size=2, flush_interval=10.0
    )

    # Create and publish two scan profile events
    event1 = ScanProfileDBEvent(
        operation_type=OperationType.CREATE,
        valid_time=datetime(2023, 1, 1),
        new_data=empty_scan_profile,
        reference="test|reference1",
        client="test",
    )
    event2 = ScanProfileDBEvent(
        operation_type=OperationType.CREATE,
        valid_time=datetime(2023, 1, 1),
        new_data=empty_scan_profile,
        reference="test|reference2",
        client="test",
    )

    manager.publish(event1)
    manager.publish(event2)

    # Verify that events have been sent as a batch
    celery_mock.send_task.assert_called_once()

    # Verify that scan profile mutations have been published
    assert channel_mock.basic_publish.call_count == 2
