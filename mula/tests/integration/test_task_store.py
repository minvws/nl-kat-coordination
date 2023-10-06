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

    def test_get_status_counts(self):
        # Arrange
        one_hour = datetime.now(timezone.utc) - timedelta(hours=1)
        four_hours = datetime.now(timezone.utc) - timedelta(hours=4)
        twenty_three_hours = datetime.now(timezone.utc) - timedelta(hours=23)
        twenty_five_hours = datetime.now(timezone.utc) - timedelta(hours=25)

        for r, status, modified_at in zip(
            (
                range(2),
                range(2),
                range(2),
                range(2),
                range(2),
            ),
            (
                models.TaskStatus.QUEUED,
                models.TaskStatus.COMPLETED,
                models.TaskStatus.FAILED,
                models.TaskStatus.DISPATCHED,
                models.TaskStatus.DISPATCHED,
            ),
            (
                one_hour,
                four_hours,
                one_hour,
                twenty_five_hours,
                twenty_three_hours,
            ),
        ):
            for _ in r:
                p_item = functions.create_p_item(self.organisation.id, 1)
                task = models.Task(
                    id=p_item.id,
                    hash=p_item.hash,
                    type=functions.TestModel.type,
                    scheduler_id=p_item.scheduler_id,
                    p_item=p_item,
                    status=status,
                    modified_at=modified_at,
                )
                self.mock_ctx.datastores.task_store.create_task(task)

        # Act
        results = self.mock_ctx.datastores.task_store.get_status_counts()

        # Assert
        self.assertEqual(results[models.TaskStatus.QUEUED], 2)
        self.assertEqual(results[models.TaskStatus.COMPLETED], 2)
        self.assertEqual(results[models.TaskStatus.FAILED], 2)
        self.assertEqual(results[models.TaskStatus.DISPATCHED], 4)

    def test_get_status_count_per_hour(self):
        # Arrange
        one_hour = datetime.now(timezone.utc) - timedelta(hours=1)
        four_hours = datetime.now(timezone.utc) - timedelta(hours=4)
        twenty_three_hours = datetime.now(timezone.utc) - timedelta(hours=23)
        twenty_five_hours = datetime.now(timezone.utc) - timedelta(hours=25)

        for r, status, modified_at in zip(
            (
                range(2),
                range(2),
                range(2),
                range(2),
                range(2),
            ),
            (
                models.TaskStatus.QUEUED,
                models.TaskStatus.COMPLETED,
                models.TaskStatus.FAILED,
                models.TaskStatus.DISPATCHED,
                models.TaskStatus.DISPATCHED,
            ),
            (
                one_hour,
                four_hours,
                one_hour,
                twenty_five_hours,
                twenty_three_hours,
            ),
        ):
            for _ in r:
                p_item = functions.create_p_item(self.organisation.id, 1)
                task = models.Task(
                    id=p_item.id,
                    hash=p_item.hash,
                    type=functions.TestModel.type,
                    scheduler_id=p_item.scheduler_id,
                    p_item=p_item,
                    status=status,
                    modified_at=modified_at,
                )
                self.mock_ctx.datastores.task_store.create_task(task)

        # Act
        results = self.mock_ctx.datastores.task_store.get_status_count_per_hour()
        keys = [k for k in results]

        # Assert
        self.assertEqual(len(results), 3)
        self.assertEqual(results.get(keys[0]).get("dispatched"), 2)
        self.assertEqual(results.get(keys[0]).get("total"), 2)
        self.assertEqual(results.get(keys[1]).get("completed"), 2)
        self.assertEqual(results.get(keys[1]).get("total"), 2)
        self.assertEqual(results.get(keys[2]).get("queued"), 2)
