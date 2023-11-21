import unittest
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest import mock

from scheduler import config, models, storage
from scheduler.storage import filters

from tests.factories import OrganisationFactory
from tests.utils import functions


class EventStoreTestCase(unittest.TestCase):
    def setUp(self):
        # Application Context
        self.mock_ctx = mock.patch("scheduler.context.AppContext").start()
        self.mock_ctx.config = config.settings.Settings()

        # Database
        self.dbconn = storage.DBConn(str(self.mock_ctx.config.db_uri))
        models.Base.metadata.create_all(self.dbconn.engine)
        self.mock_ctx.datastores = SimpleNamespace(
            **{
                storage.TaskStore.name: storage.TaskStore(self.dbconn),
                storage.PriorityQueueStore.name: storage.PriorityQueueStore(self.dbconn),
                storage.EventStore.name: storage.EventStore(self.dbconn),
            }
        )

        models.TaskDB.set_event_store(self.mock_ctx.datastores.event_store)

        # Organisation
        self.organisation = OrganisationFactory()

    def tearDown(self):
        models.Base.metadata.drop_all(self.dbconn.engine)
        self.dbconn.engine.dispose()

    def test_record_event_trigger(self):
        # Arrange
        p_item = functions.create_p_item(self.organisation.id, 1)
        task = functions.create_task(p_item)
        task_db = self.mock_ctx.datastores.task_store.create_task(task)

        # Act
        task_db.status = models.TaskStatus.DISPATCHED
        self.mock_ctx.datastores.task_store.update_task(task_db)

        task_db.status = models.TaskStatus.COMPLETED
        self.mock_ctx.datastores.task_store.update_task(task_db)

        # Assert
        events = self.mock_ctx.datastores.event_store.get_events()
        self.assertGreater(len(events), 0)

    def test_get_task_duration(self):
        # Arrange
        p_item = functions.create_p_item(self.organisation.id, 1)
        task = functions.create_task(p_item)
        task_db = self.mock_ctx.datastores.task_store.create_task(task)

        # Act
        task_db.status = models.TaskStatus.DISPATCHED
        self.mock_ctx.datastores.task_store.update_task(task_db)

        task_db.status = models.TaskStatus.COMPLETED
        self.mock_ctx.datastores.task_store.update_task(task_db)

        # Assert
        duration = self.mock_ctx.datastores.event_store.get_task_duration(task.id)
        self.assertGreater(duration, 0)

    def test_get_task_queued(self):
        # Arrange
        p_item = functions.create_p_item(self.organisation.id, 1)
        task = functions.create_task(p_item)
        task_db = self.mock_ctx.datastores.task_store.create_task(task)

        # Act
        task_db.status = models.TaskStatus.DISPATCHED
        self.mock_ctx.datastores.task_store.update_task(task_db)

        task_db.status = models.TaskStatus.COMPLETED
        self.mock_ctx.datastores.task_store.update_task(task_db)

        # Assert
        queued = self.mock_ctx.datastores.event_store.get_task_queued(task.id)
        self.assertGreater(queued, 0)

    def test_get_task_runtime(self):
        # Arrange
        p_item = functions.create_p_item(self.organisation.id, 1)
        task = functions.create_task(p_item)
        task_db = self.mock_ctx.datastores.task_store.create_task(task)

        # Act
        task_db.status = models.TaskStatus.DISPATCHED
        self.mock_ctx.datastores.task_store.update_task(task_db)

        task_db.status = models.TaskStatus.COMPLETED
        self.mock_ctx.datastores.task_store.update_task(task_db)

        # Assert
        runtime = self.mock_ctx.datastores.event_store.get_task_runtime(task.id)
        self.assertGreater(runtime, 0)

    def test_create_event(self):
        # Arrange
        event = models.Event(
            task_id=uuid.uuid4(),
            type="events.db",
            context="task",
            event="insert",
            timestamp=datetime.now(timezone.utc),
            data={"test": "test"},
        )

        # Act
        self.mock_ctx.datastores.event_store.create_event(event)

        # Assert
        events, count = self.mock_ctx.datastores.event_store.get_events()
        self.assertEqual(count, 1)
        self.assertEqual(events[0].task_id, event.task_id)

    def test_get_events(self):
        # Arrange
        first_event = models.Event(
            task_id=uuid.uuid4(),
            type="events.db",
            context="task",
            event="insert",
            timestamp=datetime.now(timezone.utc),
            data={"test": "test"},
        )

        second_event = models.Event(
            task_id=uuid.uuid4(),
            type="events.db",
            context="task",
            event="insert",
            timestamp=datetime.now(timezone.utc),
            data={"test": "test"},
        )

        # Act
        self.mock_ctx.datastores.event_store.create_event(first_event)
        self.mock_ctx.datastores.event_store.create_event(second_event)

        # Assert
        events, count = self.mock_ctx.datastores.event_store.get_events()
        self.assertEqual(count, 2)
        self.assertEqual(events[0].task_id, second_event.task_id)
        self.assertEqual(events[1].task_id, first_event.task_id)

    def test_get_events_task_id(self):
        pass

    def test_get_events_filter(self):
        # Arrange
        first_event = models.Event(
            task_id=uuid.uuid4(),
            type="events.db",
            context="task",
            event="insert",
            timestamp=datetime.now(timezone.utc),
            data={"test": "test"},
        )

        second_event = models.Event(
            task_id=uuid.uuid4(),
            type="events.db",
            context="task",
            event="insert",
            timestamp=datetime.now(timezone.utc),
            data={"test": "test"},
        )

        # Act
        first_event_db = self.mock_ctx.datastores.event_store.create_event(first_event)
        self.mock_ctx.datastores.event_store.create_event(second_event)

        # Assert
        f_req = filters.FilterRequest(
            filters=[
                filters.Filter(
                    column="task_id",
                    field=None,
                    operator="eq",
                    value=first_event_db.task_id.hex,
                )
            ],
        )

        events, count = self.mock_ctx.datastores.event_store.get_events(filters=f_req)
        self.assertEqual(count, 1)
        self.assertEqual(events[0].task_id, first_event.task_id)
