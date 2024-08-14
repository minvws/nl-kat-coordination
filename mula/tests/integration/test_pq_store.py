import unittest
import uuid
from types import SimpleNamespace
from unittest import mock

from scheduler import config, models, storage

from tests.factories import OrganisationFactory
from tests.utils import functions


class PriorityQueueStoreTestCase(unittest.TestCase):
    def setUp(self):
        # Application Context
        self.mock_ctx = mock.patch("scheduler.context.AppContext").start()
        self.mock_ctx.config = config.settings.Settings()

        # Database
        self.dbconn = storage.DBConn(str(self.mock_ctx.config.db_uri))
        self.dbconn.connect()
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
        item = functions.create_item(scheduler_id=uuid.uuid4().hex, priority=1)
        item.status = models.TaskStatus.QUEUED
        created_item = self.mock_ctx.datastores.pq_store.push(item)

        item_db = self.mock_ctx.datastores.pq_store.get(scheduler_id=item.scheduler_id, item_id=item.id)

        # Assert
        self.assertIsNotNone(created_item)
        self.assertIsNotNone(item_db)
        self.assertEqual(item_db.id, created_item.id)

    def test_push_status_not_queued(self):
        item = functions.create_item(scheduler_id=uuid.uuid4().hex, priority=1)
        item.status = models.TaskStatus.PENDING
        created_item = self.mock_ctx.datastores.pq_store.push(item)

        item_db = self.mock_ctx.datastores.pq_store.get(scheduler_id=item.scheduler_id, item_id=item.id)

        # Assert
        self.assertIsNotNone(created_item)
        self.assertIsNone(item_db)

    def test_pop(self):
        # Arrange
        item = functions.create_item(scheduler_id=uuid.uuid4().hex, priority=1)
        item.status = models.TaskStatus.QUEUED
        created_item = self.mock_ctx.datastores.pq_store.push(item)

        popped_item = self.mock_ctx.datastores.pq_store.pop(item.scheduler_id)

        # Assert
        self.assertIsNotNone(popped_item)
        self.assertEqual(popped_item.id, created_item.id)

    def test_pop_status_not_queued(self):
        # Arrange
        item = functions.create_item(scheduler_id=uuid.uuid4().hex, priority=1)
        item.status = models.TaskStatus.PENDING
        created_item = self.mock_ctx.datastores.pq_store.push(item)

        popped_item = self.mock_ctx.datastores.pq_store.pop(item.scheduler_id)

        # Assert
        self.assertIsNotNone(created_item)
        self.assertIsNone(popped_item)
