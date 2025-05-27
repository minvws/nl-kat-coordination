from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from pydantic import TypeAdapter

from octopoes.events.events import OOIDBEvent, OperationType
from octopoes.models.ooi.network import Network
from octopoes.tasks.tasks import handle_event_batch
from octopoes.xtdb.client import XTDBSession


@pytest.fixture
def mock_type_adapter():
    """Mock TypeAdapter to return predefined events."""
    mock_adapter = Mock(spec=TypeAdapter)
    return mock_adapter


@pytest.fixture
def mock_xtdb_session():
    """Mock XTDBSession."""
    return Mock(spec=XTDBSession)


@pytest.fixture
def mock_octopoes_service():
    """Mock OctopoesService."""
    mock_service = Mock()
    return mock_service


@patch("octopoes.tasks.tasks.get_xtdb_client")
@patch("octopoes.tasks.tasks.bootstrap_octopoes")
@patch("octopoes.tasks.tasks.TypeAdapter")
def test_handle_event_batch_empty(mock_type_adapter, mock_bootstrap, mock_get_xtdb_client):
    """Test handling an empty batch of events."""
    # Call with empty list
    handle_event_batch([])

    # Verify that no processing was done
    mock_type_adapter.assert_not_called()
    mock_bootstrap.assert_not_called()
    mock_get_xtdb_client.assert_not_called()


@patch("octopoes.tasks.tasks.get_xtdb_client")
@patch("octopoes.tasks.tasks.bootstrap_octopoes")
@patch("octopoes.tasks.tasks.TypeAdapter")
@patch("octopoes.tasks.tasks.timeit.default_timer")
def test_handle_event_batch_single_client(
    mock_timer, mock_type_adapter, mock_bootstrap, mock_get_xtdb_client, mock_xtdb_session, mock_octopoes_service
):
    """Test handling a batch of events from a single client."""
    # Setup mocks
    mock_timer.side_effect = [0.0, 1.0]  # Start and end times
    mock_get_xtdb_client.return_value = "xtdb_client"
    mock_bootstrap.return_value = mock_octopoes_service

    # Create test events
    network = Network(name="internet")
    event1 = OOIDBEvent(
        operation_type=OperationType.CREATE, valid_time=datetime(2023, 1, 1), new_data=network, client="test_client"
    )
    event2 = OOIDBEvent(
        operation_type=OperationType.UPDATE, valid_time=datetime(2023, 1, 1), new_data=network, client="test_client"
    )

    # Setup TypeAdapter mock to return our test events
    mock_adapter = Mock()
    mock_adapter.validate_python.side_effect = [event1, event2]
    mock_type_adapter.return_value = mock_adapter

    # Call handle_event_batch with event dictionaries
    handle_event_batch([{"event": "data1"}, {"event": "data2"}])

    # Verify that events were processed correctly
    assert mock_adapter.validate_python.call_count == 2
    mock_get_xtdb_client.assert_called_once_with("None", "test_client")
    mock_bootstrap.assert_called_once()

    # Verify that process_events was called with both events
    mock_octopoes_service.process_events.assert_called_once()
    events_processed = mock_octopoes_service.process_events.call_args[0][0]
    assert len(events_processed) == 2
    assert events_processed[0] == event1
    assert events_processed[1] == event2

    # Verify that session was committed
    mock_octopoes_service.session.commit.assert_called_once()


@patch("octopoes.tasks.tasks.get_xtdb_client")
@patch("octopoes.tasks.tasks.bootstrap_octopoes")
@patch("octopoes.tasks.tasks.TypeAdapter")
def test_handle_event_batch_multiple_clients(
    mock_type_adapter, mock_bootstrap, mock_get_xtdb_client, mock_xtdb_session, mock_octopoes_service
):
    """Test handling a batch of events from multiple clients."""
    # Setup mocks
    mock_get_xtdb_client.return_value = "xtdb_client"
    mock_bootstrap.return_value = mock_octopoes_service

    # Create test events for different clients
    network = Network(name="internet")
    event1 = OOIDBEvent(
        operation_type=OperationType.CREATE, valid_time=datetime(2023, 1, 1), new_data=network, client="client1"
    )
    event2 = OOIDBEvent(
        operation_type=OperationType.UPDATE, valid_time=datetime(2023, 1, 1), new_data=network, client="client2"
    )

    # Setup TypeAdapter mock to return our test events
    mock_adapter = Mock()
    mock_adapter.validate_python.side_effect = [event1, event2]
    mock_type_adapter.return_value = mock_adapter

    # Call handle_event_batch with event dictionaries
    handle_event_batch([{"event": "data1"}, {"event": "data2"}])

    # Verify that events were processed correctly
    assert mock_adapter.validate_python.call_count == 2

    # Verify that get_xtdb_client was called for each client
    assert mock_get_xtdb_client.call_count == 2
    mock_get_xtdb_client.assert_any_call("None", "client1")
    mock_get_xtdb_client.assert_any_call("None", "client2")

    # Verify that bootstrap_octopoes was called for each client
    assert mock_bootstrap.call_count == 2

    # Verify that process_events was called for each client
    assert mock_octopoes_service.process_events.call_count == 2

    # Verify that session was committed for each client
    assert mock_octopoes_service.session.commit.call_count == 2


@patch("octopoes.tasks.tasks.get_xtdb_client")
@patch("octopoes.tasks.tasks.bootstrap_octopoes")
@patch("octopoes.tasks.tasks.TypeAdapter")
@patch("octopoes.tasks.tasks.logger")
def test_handle_event_batch_exception(mock_logger, mock_type_adapter, mock_bootstrap, mock_get_xtdb_client):
    """Test handling exceptions in event batch processing."""
    # Setup mocks to raise an exception
    mock_adapter = Mock()
    mock_adapter.validate_python.side_effect = ValueError("Test error")
    mock_type_adapter.return_value = mock_adapter

    # Call handle_event_batch with event dictionaries
    with pytest.raises(ValueError):
        handle_event_batch([{"event": "data1"}])

    # Verify that the exception was logged
    mock_logger.exception.assert_called_once()
