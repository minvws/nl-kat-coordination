import unittest
from types import SimpleNamespace
from unittest import mock

from scheduler import config, models, schedulers, storage

from tests.factories import OrganisationFactory


class ReportSchedulerBaseTestCase(unittest.TestCase):
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
                storage.TaskStore.name: storage.TaskStore(self.dbconn),
                storage.PriorityQueueStore.name: storage.PriorityQueueStore(self.dbconn),
                storage.ScheduleStore.name: storage.ScheduleStore(self.dbconn),
            }
        )

        # Scheduler
        self.organisation = OrganisationFactory()
        self.scheduler = schedulers.ReportScheduler(
            ctx=self.mock_ctx,
            scheduler_id=self.organisation.id,
            organisation=self.organisation,
        )

    def tearDown(self):
        self.scheduler.stop()
        models.Base.metadata.drop_all(self.dbconn.engine)
        self.dbconn.engine.dispose()


class ReportSchedulerTestCase(ReportSchedulerBaseTestCase):
    def setUp(self):
        super().setUp()

        self.mock_get_schedules = mock.patch(
            "scheduler.context.AppContext.datastores.schedule_store.get_schedules",
        ).start()

    def tearDown(self):
        mock.patch.stopall()

    def test_enable_scheduler(self):
        # Disable scheduler first
        self.scheduler.disable()

        # Threads should be stopped
        self.assertEqual(0, len(self.scheduler.threads))

        # Queue should be empty
        self.assertEqual(0, self.scheduler.queue.qsize())

        # Re-enable scheduler
        self.scheduler.enable()

        # Threads should be started
        self.assertGreater(len(self.scheduler.threads), 0)

        # Scheduler should be enabled
        self.assertTrue(self.scheduler.is_enabled())

        # Stop the scheduler
        self.scheduler.stop()

    def test_disable_scheduler(self):
        # Disable scheduler
        self.scheduler.disable()

        # Threads should be stopped
        self.assertEqual(0, len(self.scheduler.threads))

        # Queue should be empty
        self.assertEqual(0, self.scheduler.queue.qsize())

        # Scheduler should be disabled
        self.assertFalse(self.scheduler.is_enabled())

    def test_push_tasks_for_rescheduling(self):
        """When the deadline of schedules have passed, the resulting task should be added to the queue"""
        # Arrange
        report_task = models.ReportTask(
            organisation_id=self.organisation.id,
            report_recipe_id="123",
        )

        schedule = models.Schedule(
            scheduler_id=self.scheduler.scheduler_id,
            hash=report_task.hash,
            data=report_task.dict(),
        )

        schedule_db = self.mock_ctx.datastores.schedule_store.create_schedule(schedule)

        # Mocks
        self.mock_get_schedules.return_value = ([schedule_db], 1)

        # Act
        self.scheduler.push_tasks_for_rescheduling()

        # Assert: new item should be on queue
        self.assertEqual(1, self.scheduler.queue.qsize())

        # Assert: new item is created with a similar task
        peek = self.scheduler.queue.peek(0)
        self.assertEqual(schedule.hash, peek.hash)

        # Assert: task should be created, and should be the one that is queued
        task_db = self.mock_ctx.datastores.task_store.get_task(peek.id)
        self.assertIsNotNone(task_db)
        self.assertEqual(peek.id, task_db.id)

    def test_push_tasks_for_rescheduling_item_on_queue(self):
        """When the deadline of schedules have passed, the resulting task should be added to the queue"""
        # Arrange
        report_task = models.ReportTask(
            organisation_id=self.organisation.id,
            report_recipe_id="123",
        )

        schedule = models.Schedule(
            scheduler_id=self.scheduler.scheduler_id,
            hash=report_task.hash,
            data=report_task.dict(),
        )

        schedule_db = self.mock_ctx.datastores.schedule_store.create_schedule(schedule)

        # Mocks
        self.mock_get_schedules.return_value = ([schedule_db], 1)

        # Act
        self.scheduler.push_tasks_for_rescheduling()

        # Assert: new item should be on queue
        self.assertEqual(1, self.scheduler.queue.qsize())

        # Assert: new item is created with a similar task
        peek = self.scheduler.queue.peek(0)
        self.assertEqual(schedule.hash, peek.hash)

        # Assert: task should be created, and should be the one that is queued
        task_db = self.mock_ctx.datastores.task_store.get_task(peek.id)
        self.assertIsNotNone(task_db)
        self.assertEqual(peek.id, task_db.id)

        # Act: push again
        self.scheduler.push_tasks_for_rescheduling()

        # Should only be one task on queue
        self.assertEqual(1, self.scheduler.queue.qsize())
