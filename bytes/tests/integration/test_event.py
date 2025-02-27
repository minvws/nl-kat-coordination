import json
from datetime import datetime

from bytes.events.events import RawFileReceived
from bytes.rabbitmq import RabbitMQEventManager
from tests.loading import get_raw_data_meta


def test_event_published_successfully(event_manager: RabbitMQEventManager) -> None:
    test_organization = "test"
    raw_data_meta = get_raw_data_meta()

    # We use an isolated queue this way to not conflict with other integration tests
    raw_data_meta.boefje_meta.organization = test_organization

    event = RawFileReceived(
        created_at=datetime(2000, 10, 10, 10), organization=test_organization, raw_data=raw_data_meta
    )
    event_manager.publish(event)
    method, properties, body = event_manager.connection.channel().basic_get(event_manager._queue_name(event))

    response = json.loads(body)
    event_manager.connection.channel().basic_ack(method.delivery_tag)

    assert response["organization"] == test_organization
    assert response["raw_data"] == json.loads(event.raw_data.model_dump_json())
    assert response["created_at"] == "2000-10-10T10:00:00"
