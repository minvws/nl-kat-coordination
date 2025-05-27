from octopoes.events.events import OOIDBEvent, OperationType, OriginDBEvent, ScanProfileDBEvent
from octopoes.models import EmptyScanProfile, Reference
from octopoes.models.ooi.network import Network
from octopoes.models.origin import Origin, OriginType


def test_process_events_empty(octopoes_service):
    """Test processing an empty list of events."""
    # Call with empty list
    octopoes_service.process_events([])

    # Verify that no processing was done
    octopoes_service.process_event.assert_not_called()


def test_process_events_single_type(octopoes_service, valid_time):
    """Test processing multiple events of the same type."""
    # Create test events of the same type
    network1 = Network(name="network1")
    network2 = Network(name="network2")

    event1 = OOIDBEvent(operation_type=OperationType.CREATE, valid_time=valid_time, client="_dev", new_data=network1)
    event2 = OOIDBEvent(operation_type=OperationType.CREATE, valid_time=valid_time, client="_dev", new_data=network2)

    # Process events
    octopoes_service.process_events([event1, event2])

    # Verify that each event was processed
    assert octopoes_service.process_event.call_count == 2
    octopoes_service.process_event.assert_any_call(event1)
    octopoes_service.process_event.assert_any_call(event2)


def test_process_events_multiple_types(octopoes_service, valid_time):
    """Test processing events of different types."""
    # Create test events of different types
    network = Network(name="network1")

    ooi_event = OOIDBEvent(operation_type=OperationType.CREATE, valid_time=valid_time, client="_dev", new_data=network)

    origin_event = OriginDBEvent(
        operation_type=OperationType.CREATE,
        valid_time=valid_time,
        client="_dev",
        new_data=Origin(
            origin_type=OriginType.OBSERVATION, method="test-method", source=Reference.from_str("Network|network1")
        ),
    )

    scan_profile_event = ScanProfileDBEvent(
        operation_type=OperationType.CREATE,
        valid_time=valid_time,
        client="_dev",
        new_data=EmptyScanProfile(reference=Reference.from_str("Network|network1")),
        reference="Network|network1",
    )

    # Process events
    octopoes_service.process_events([ooi_event, origin_event, scan_profile_event])

    # Verify that each event was processed
    assert octopoes_service.process_event.call_count == 3
    octopoes_service.process_event.assert_any_call(ooi_event)
    octopoes_service.process_event.assert_any_call(origin_event)
    octopoes_service.process_event.assert_any_call(scan_profile_event)


def test_process_events_order(octopoes_service, valid_time):
    """Test that events are processed in the correct order (delete, update, create)."""
    # Create test events with different operation types
    network = Network(name="network1")

    create_event = OOIDBEvent(
        operation_type=OperationType.CREATE, valid_time=valid_time, client="_dev", new_data=network
    )

    update_event = OOIDBEvent(
        operation_type=OperationType.UPDATE, valid_time=valid_time, client="_dev", new_data=network, old_data=network
    )

    delete_event = OOIDBEvent(
        operation_type=OperationType.DELETE, valid_time=valid_time, client="_dev", old_data=network
    )

    # Process events in mixed order
    octopoes_service.process_events([create_event, update_event, delete_event])

    # Verify that events were processed in the correct order: delete, update, create
    assert octopoes_service.process_event.call_count == 3
    call_order = [call[0][0] for call in octopoes_service.process_event.call_args_list]

    # Find the positions of each event type in the call order
    delete_pos = call_order.index(delete_event)
    update_pos = call_order.index(update_event)
    create_pos = call_order.index(create_event)

    # Verify the order
    assert delete_pos < update_pos < create_pos


def test_process_events_entity_type_order(octopoes_service, valid_time):
    """Test that events are processed in the correct entity type order."""
    # Create test events with different entity types
    network = Network(name="network1")

    ooi_event = OOIDBEvent(operation_type=OperationType.CREATE, valid_time=valid_time, client="_dev", new_data=network)

    origin_event = OriginDBEvent(
        operation_type=OperationType.CREATE,
        valid_time=valid_time,
        client="_dev",
        new_data=Origin(
            origin_type=OriginType.OBSERVATION, method="test-method", source=Reference.from_str("Network|network1")
        ),
    )

    scan_profile_event = ScanProfileDBEvent(
        operation_type=OperationType.CREATE,
        valid_time=valid_time,
        client="_dev",
        new_data=EmptyScanProfile(reference=Reference.from_str("Network|network1")),
        reference="Network|network1",
    )

    # Process events in mixed order
    octopoes_service.process_events([scan_profile_event, origin_event, ooi_event])

    # Verify that events were processed in the correct order: ooi, origin, scan_profile
    assert octopoes_service.process_event.call_count == 3
    call_order = [call[0][0] for call in octopoes_service.process_event.call_args_list]

    # Find the positions of each event type in the call order
    ooi_pos = call_order.index(ooi_event)
    origin_pos = call_order.index(origin_event)
    scan_profile_pos = call_order.index(scan_profile_event)

    # Verify the order
    assert ooi_pos < origin_pos < scan_profile_pos


def test_process_events_exception_handling(octopoes_service, valid_time):
    """Test that exceptions in event processing are handled correctly."""
    # Create test events
    network1 = Network(name="network1")
    network2 = Network(name="network2")

    event1 = OOIDBEvent(operation_type=OperationType.CREATE, valid_time=valid_time, client="_dev", new_data=network1)
    event2 = OOIDBEvent(operation_type=OperationType.CREATE, valid_time=valid_time, client="_dev", new_data=network2)

    # Make the first event raise an exception
    octopoes_service.process_event.side_effect = [ValueError("Test error"), None]

    # Process events
    octopoes_service.process_events([event1, event2])

    # Verify that both events were attempted to be processed
    assert octopoes_service.process_event.call_count == 2
    octopoes_service.process_event.assert_any_call(event1)
    octopoes_service.process_event.assert_any_call(event2)
