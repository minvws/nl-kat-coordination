import unittest
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import mock

from scheduler import config, models, storage
from scheduler.storage import filters
from tests.factories import OrganisationFactory
from tests.utils import functions


class PriorityQueueStoreTestCase(unittest.TestCase):
    def setUp(self):
        # Application Context
        self.mock_ctx = mock.patch("scheduler.context.AppContext").start()
        self.mock_ctx.config = config.settings.Settings()

        # Database
        self.dbconn = storage.DBConn(str(self.mock_ctx.config.db_uri))
        models.Base.metadata.drop_all(self.dbconn.engine)
        models.Base.metadata.create_all(self.dbconn.engine)

        self.mock_ctx.datastores = SimpleNamespace(
            **{
                storage.PriorityQueueStore.name: storage.PriorityQueueStore(self.dbconn),
                storage.TaskStore.name: storage.TaskStore(self.dbconn),
            }
        )

        # Organisation
        self.organisation = OrganisationFactory()

    def tearDown(self):
        models.Base.metadata.drop_all(self.dbconn.engine)
        self.dbconn.engine.dispose()

    def test_push(self):
        # Arrange
        task = functions.create_task()
        p_item = functions.create_p_item(scheduler_id=uuid.uuid4().hex, priority=1, task=task)
        self.mock_ctx.datastores.pq_store.push(p_item.scheduler_id, p_item)

        created_p_item = self.mock_ctx.datastores.pq_store.get(scheduler_id=p_item.scheduler_id, item_id=p_item.id)
        created_task = self.mock_ctx.datastores.task_store.get_task(task.id)

        # Assert
        self.assertIsNotNone(created_p_item)
        self.assertIsNotNone(created_task)
        self.assertEqual(created_p_item.task_id, created_task.id)

    def test_pop(self):
        # Arrange
        task = functions.create_task()
        p_item = functions.create_p_item(scheduler_id=uuid.uuid4().hex, priority=1, task=task)
        created_p_item = self.mock_ctx.datastores.pq_store.push(p_item.scheduler_id, p_item)

        popped_item = self.mock_ctx.datastores.pq_store.pop(p_item.scheduler_id)

        # Assert
        self.assertIsNotNone(popped_item)
        self.assertEqual(popped_item.id, created_p_item.id)
        self.assertEqual(popped_item.task_id, task.id)

    def test_task_relationship(self):
        pass
