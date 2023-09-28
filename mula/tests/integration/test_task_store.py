import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import mock

from scheduler import config, models, storage

from tests.factories import OrganisationFactory
from tests.utils import functions


class TaskStoreTestCase(unittest.TestCase):
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
            }
        )

        # Organisation
        self.organisation = OrganisationFactory()

    def tearDown(self):
        models.Base.metadata.drop_all(self.dbconn.engine)
        self.dbconn.engine.dispose()

    def test_get_status_count_per_hour(self):
        # Arrange
        p_items = []
        for _ in range(10):
            p_items.append(functions.create_p_item(self.organisation.id, 1))

        for p_item in p_items[:2]:
            task = models.Task(
                id=p_item.id,
                hash=p_item.hash,
                type=functions.TestModel.type,
                scheduler_id=p_item.scheduler_id,
                p_item=p_item,
                status=models.TaskStatus.QUEUED,
                modified_at=datetime.now(timezone.utc) - timedelta(hours=1),
            )

            self.mock_ctx.datastores.task_store.create_task(task)

        for p_item in p_items[2:4]:
            task = models.Task(
                id=p_item.id,
                hash=p_item.hash,
                type=functions.TestModel.type,
                scheduler_id=p_item.scheduler_id,
                p_item=p_item,
                status=models.TaskStatus.COMPLETED,
                modified_at=datetime.now(timezone.utc) - timedelta(hours=4),
            )

            self.mock_ctx.datastores.task_store.create_task(task)

        for p_item in p_items[4:6]:
            task = models.Task(
                id=p_item.id,
                hash=p_item.hash,
                type=functions.TestModel.type,
                scheduler_id=p_item.scheduler_id,
                p_item=p_item,
                status=models.TaskStatus.FAILED,
                modified_at=datetime.now(timezone.utc) - timedelta(hours=1),
            )

            self.mock_ctx.datastores.task_store.create_task(task)

        for p_item in p_items[6:8]:
            task = models.Task(
                id=p_item.id,
                hash=p_item.hash,
                type=functions.TestModel.type,
                scheduler_id=p_item.scheduler_id,
                p_item=p_item,
                status=models.TaskStatus.DISPATCHED,
                modified_at=datetime.now(timezone.utc) - timedelta(hours=25),
            )

            self.mock_ctx.datastores.task_store.create_task(task)

        # Act
        self.mock_ctx.datastores.task_store.get_status_count_per_hour()
