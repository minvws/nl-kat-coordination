import unittest
from types import SimpleNamespace
from unittest import mock

from scheduler import config, models, storage
from tests.utils import functions


class ScheduleStore(unittest.TestCase):
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
                storage.TaskStore.name: storage.TaskStore(self.dbconn),
                storage.ScheduleStore.name: storage.ScheduleStore(self.dbconn),
            }
        )

    def tearDown(self):
        models.Base.metadata.drop_all(self.dbconn.engine)
        self.dbconn.engine.dispose()

    def test_create_schedule(self):
        # Arrange
        scheduler_id = "test_scheduler_id"
        schedule = models.Schedule(
            scheduler_id=scheduler_id,
            p_item=functions.create_p_item(scheduler_id=scheduler_id, priority=1),
        )

        # Act
        schedule_db = self.mock_ctx.datastores.schedule_store.create_schedule(schedule)

        # Assert
        self.assertEqual(schedule, self.mock_ctx.datastores.schedule_store.get_schedule_by_id(schedule_db.id))

    def test_get_schedules(self):
        # Arrange
        scheduler_one = "test_scheduler_one"
        for i in range(5):
            schedule = models.Schedule(
                scheduler_id=scheduler_one,
                p_item=functions.create_p_item(scheduler_id=scheduler_one, priority=i),
            )
            self.mock_ctx.datastores.schedule_store.create_schedule(schedule)

        scheduler_two = "test_scheduler_two"
        for i in range(5):
            schedule = models.Schedule(
                scheduler_id=scheduler_two,
                p_item=functions.create_p_item(scheduler_id=scheduler_two, priority=i),
            )
            self.mock_ctx.datastores.schedule_store.create_schedule(schedule)

        # Act
        schedules_scheduler_one, schedules_scheduler_one_count = self.mock_ctx.datastores.schedule_store.get_schedules(
            scheduler_id=scheduler_one,
        )
        schedules_scheduler_two, schedules_scheduler_two_count = self.mock_ctx.datastores.schedule_store.get_schedules(
            scheduler_id=scheduler_two,
        )

        # Assert
        self.assertEqual(5, len(schedules_scheduler_one))
        self.assertEqual(5, schedules_scheduler_one_count)
        self.assertEqual(5, len(schedules_scheduler_two))
        self.assertEqual(5, schedules_scheduler_two_count)

    def test_get_schedule_by_id(self):
        # Arrange
        scheduler_id = "test_scheduler_id"
        schedule = models.Schedule(
            scheduler_id=scheduler_id,
            p_item=functions.create_p_item(scheduler_id=scheduler_id, priority=1),
        )
        schedule_db = self.mock_ctx.datastores.schedule_store.create_schedule(schedule)

        # Act
        schedule_by_id = self.mock_ctx.datastores.schedule_store.get_schedule_by_id(schedule_db.id)

        # Assert
        self.assertEqual(schedule_by_id.id, schedule_db.id)

    def test_get_schedule_by_hash(self):
        # Arrange
        scheduler_id = "test_scheduler_id"
        schedule = models.Schedule(
            scheduler_id=scheduler_id,
            p_item=functions.create_p_item(scheduler_id=scheduler_id, priority=1),
        )
        schedule_db = self.mock_ctx.datastores.schedule_store.create_schedule(schedule)

        # Act
        schedule_by_hash = self.mock_ctx.datastores.schedule_store.get_schedule_by_hash(schedule_db.p_item.hash)

        # Assert
        self.assertEqual(schedule_by_hash.id, schedule_db.id)
        self.assertEqual(schedule_by_hash.p_item, schedule_db.p_item)
        self.assertEqual(schedule_by_hash.p_item.hash, schedule_db.p_item.hash)

    def test_update_schedule(self):
        # Arrange
        scheduler_id = "test_scheduler_id"
        schedule = models.Schedule(
            scheduler_id=scheduler_id,
            p_item=functions.create_p_item(scheduler_id=scheduler_id, priority=1),
        )
        schedule_db = self.mock_ctx.datastores.schedule_store.create_schedule(schedule)

        # Assert
        self.assertEqual(schedule_db.enabled, True)

        # Act
        schedule_db.enabled = False
        self.mock_ctx.datastores.schedule_store.update_schedule(schedule_db)

        # Assert
        schedule_db_updated = self.mock_ctx.datastores.schedule_store.get_schedule_by_id(schedule_db.id)
        self.assertEqual(schedule_db_updated.enabled, False)

    def test_update_schedule_enabled(self):
        # Arrange
        scheduler_id = "test_scheduler_id"
        schedule = models.Schedule(
            scheduler_id=scheduler_id,
            p_item=functions.create_p_item(scheduler_id=scheduler_id, priority=1),
        )
        schedule_db = self.mock_ctx.datastores.schedule_store.create_schedule(schedule)

        # Assert
        self.assertEqual(schedule_db.enabled, True)

        # Act
        self.mock_ctx.datastores.schedule_store.update_schedule_enabled(schedule_db.id, False)

        # Assert
        schedule_db_updated = self.mock_ctx.datastores.schedule_store.get_schedule_by_id(schedule_db.id)
        self.assertEqual(schedule_db_updated.enabled, False)

    def test_delete_schedule(self):
        # Arrange
        p_item = functions.create_p_item("test_scheduler_id", 1)

        schedule = models.Schedule(
            scheduler_id=p_item.scheduler_id,
            p_item=p_item,
        )
        schedule_db = self.mock_ctx.datastores.schedule_store.create_schedule(schedule)

        # Act
        self.mock_ctx.datastores.schedule_store.delete_schedule(schedule_db.id)

        # Assert
        is_schedule_deleted = self.mock_ctx.datastores.schedule_store.get_schedule_by_id(schedule_db.id)
        self.assertEqual(is_schedule_deleted, None)

    def test_delete_schedule_cascade(self):
        """When a schedule is deleted, its tasks should NOT be deleted."""
        # Arrange
        p_item = functions.create_p_item("test_scheduler_id", 1)

        schedule = models.Schedule(
            scheduler_id=p_item.scheduler_id,
            p_item=p_item,
        )
        schedule_db = self.mock_ctx.datastores.schedule_store.create_schedule(schedule)

        task = models.TaskRun(
            id=p_item.id,
            hash=p_item.hash,
            type=functions.TestModel.type,
            status=models.TaskStatus.QUEUED,
            scheduler_id=p_item.scheduler_id,
            p_item=p_item,
            schedule_id=schedule_db.id,
        )
        task_db = self.mock_ctx.datastores.task_store.create_task(task)

        # Act
        self.mock_ctx.datastores.schedule_store.delete_schedule(schedule_db.id)

        # Assert
        is_schedule_deleted = self.mock_ctx.datastores.schedule_store.get_schedule_by_id(schedule_db.id)
        self.assertEqual(is_schedule_deleted, None)

        is_task_deleted = self.mock_ctx.datastores.task_store.get_task_by_id(task_db.id)
        self.assertIsNotNone(is_task_deleted)
        self.assertIsNone(is_task_deleted.schedule_id)

    def test_relationship_schedule_tasks(self):
        # Arrange
        p_item = functions.create_p_item("test_scheduler_id", 1)

        schedule = models.Schedule(
            scheduler_id=p_item.scheduler_id,
            p_item=p_item,
        )
        schedule_db = self.mock_ctx.datastores.schedule_store.create_schedule(schedule)

        task = models.TaskRun(
            id=p_item.id,
            hash=p_item.hash,
            type=functions.TestModel.type,
            status=models.TaskStatus.QUEUED,
            scheduler_id=p_item.scheduler_id,
            p_item=p_item,
            schedule_id=schedule_db.id,
        )
        task_db = self.mock_ctx.datastores.task_store.create_task(task)

        # Act
        schedule_tasks = self.mock_ctx.datastores.schedule_store.get_schedule_by_id(schedule_db.id).tasks

        # Assert
        self.assertEqual(len(schedule_tasks), 1)
        self.assertEqual(schedule_tasks[0].id, task_db.id)
