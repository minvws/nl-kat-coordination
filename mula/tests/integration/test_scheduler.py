import unittest
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest import mock

from scheduler import config, models, queues, storage
from structlog.testing import capture_logs

from tests.mocks import item as mock_item
from tests.mocks import queue as mock_queue
from tests.mocks import scheduler as mock_scheduler
from tests.utils import functions


class SchedulerTestCase(unittest.TestCase):
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

        identifier = uuid.uuid4().hex

        queue = mock_queue.MockPriorityQueue(
            pq_id=identifier,
            maxsize=self.mock_ctx.config.pq_maxsize,
            item_type=mock_item.MockData,
            allow_priority_updates=True,
            pq_store=self.mock_ctx.datastores.pq_store,
        )

        self.scheduler = mock_scheduler.MockScheduler(
            ctx=self.mock_ctx,
            scheduler_id=identifier,
            queue=queue,
            create_schedule=True,
        )

    def tearDown(self):
        self.scheduler.stop()
        models.Base.metadata.drop_all(self.dbconn.engine)
        self.dbconn.engine.dispose()

    def test_push_items_to_queue(self):
        # Arrange
        items = []
        for i in range(10):
            item = functions.create_item(
                scheduler_id=self.scheduler.scheduler_id,
                priority=i + 1,
            )
            items.append(item)

        # Act
        self.scheduler.push_items_to_queue(items)

        # Assert
        self.assertEqual(10, self.scheduler.queue.qsize())

        for i, item in enumerate(items):
            # Task should be on priority queue
            pq_item = self.scheduler.queue.peek(i)
            self.assertEqual(pq_item.id, item.id)

            # Task should be in datastore, and queued
            task_db = self.mock_ctx.datastores.task_store.get_task(str(item.id))
            self.assertEqual(task_db.id, item.id)
            self.assertEqual(task_db.status, models.TaskStatus.QUEUED)

            # Schedule should be in datastore
            schedule_db = self.mock_ctx.datastores.schedule_store.get_schedule(task_db.schedule_id)
            self.assertIsNotNone(schedule_db)
            self.assertEqual(schedule_db.id, task_db.schedule_id)

    def test_push_item_to_queue(self):
        # Arrange
        item = functions.create_item(
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
        )

        # Act
        self.scheduler.push_item_to_queue(item)

        # Task should be on priority queue
        pq_item = self.scheduler.queue.peek(0)
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(pq_item.id, item.id)

        # Task should be in datastore, and queued
        task_db = self.mock_ctx.datastores.task_store.get_task(str(item.id))
        self.assertEqual(task_db.id, item.id)
        self.assertEqual(task_db.status, models.TaskStatus.QUEUED)

        # Schedule should be in datastore
        schedule_db = self.mock_ctx.datastores.schedule_store.get_schedule(task_db.schedule_id)
        self.assertIsNotNone(schedule_db)
        self.assertEqual(schedule_db.id, task_db.schedule_id)

    def test_push_item_to_queue_create_schedule_false(self):
        # Arrange
        self.scheduler.create_schedule = False

        item = functions.create_item(
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
        )

        # Act
        self.scheduler.push_item_to_queue(item)

        # Task should be on priority queue
        pq_item = self.scheduler.queue.peek(0)
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(pq_item.id, item.id)

        # Task should be in datastore, and queued
        task_db = self.mock_ctx.datastores.task_store.get_task(str(item.id))
        self.assertEqual(task_db.id, item.id)
        self.assertEqual(task_db.status, models.TaskStatus.QUEUED)
        self.assertIsNone(task_db.schedule_id)

        # Schedule should not be in datastore
        schedule_db = self.mock_ctx.datastores.schedule_store.get_schedule_by_hash(
            task_db.hash,
        )
        self.assertIsNone(schedule_db)

    def test_push_item_to_queue_full(self):
        # Arrange
        item = functions.create_item(
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
        )

        self.scheduler.queue.maxsize = 1

        # Act
        self.scheduler.push_item_to_queue_with_timeout(item=item, max_tries=1)

        # Assert
        self.assertEqual(1, self.scheduler.queue.qsize())

        with self.assertRaises(queues.errors.QueueFullError):
            self.scheduler.push_item_to_queue_with_timeout(item=item, max_tries=1)

        self.assertEqual(1, self.scheduler.queue.qsize())

    def test_push_item_to_queue_invalid(self):
        # Arrange
        item = functions.create_item(
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
        )
        item.data = {"invalid": "data"}

        # Assert
        with self.assertRaises(queues.errors.InvalidItemError):
            self.scheduler.push_item_to_queue(item)

    def test_pop_item_from_queue(self):
        # Arrange
        item = functions.create_item(
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
        )

        self.scheduler.push_item_to_queue(item)

        # Act
        popped_item = self.scheduler.pop_item_from_queue()

        # Assert
        self.assertEqual(0, self.scheduler.queue.qsize())
        self.assertEqual(item.id, popped_item.id)

    def test_pop_item_from_queue_empty(self):
        self.assertEqual(0, self.scheduler.queue.qsize())
        with self.assertRaises(queues.errors.QueueEmptyError):
            self.scheduler.pop_item_from_queue()

    def test_post_push(self):
        """When a task is added to the queue, it should be added to the database"""
        # Arrange
        item = functions.create_item(
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
        )

        # Act
        self.scheduler.push_item_to_queue(item)

        # Assert: Task should be on priority queue
        pq_item = self.scheduler.queue.peek(0)
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(pq_item.id, item.id)

        # Assert: Task should be in datastore, and queued
        task_db = self.mock_ctx.datastores.task_store.get_task(str(item.id))
        self.assertEqual(task_db.id, item.id)
        self.assertEqual(task_db.status, models.TaskStatus.QUEUED)

        # Assert: Schedule should be in datastore
        schedule_db = self.mock_ctx.datastores.schedule_store.get_schedule(task_db.schedule_id)
        self.assertIsNotNone(schedule_db)
        self.assertEqual(schedule_db.id, task_db.schedule_id)

        # Assert: schedule should have a deadline
        self.assertIsNotNone(schedule_db.deadline_at)
        self.assertIsNotNone(schedule_db.schedule)

        # Assert: deadline should be in the future, at least later than the
        # grace period
        self.assertGreater(
            schedule_db.deadline_at,
            datetime.now(timezone.utc),
        )

    def test_post_push_schedule_enabled(self):
        # Arrange
        item = functions.create_item(
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
        )

        # Act
        self.scheduler.push_item_to_queue(item)

        # Assert: Task should be on priority queue
        pq_item = self.scheduler.queue.peek(0)
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(pq_item.id, item.id)

        # Assert: Task should be in datastore, and queued
        task_db = self.mock_ctx.datastores.task_store.get_task(str(item.id))
        self.assertEqual(task_db.id, item.id)
        self.assertEqual(task_db.status, models.TaskStatus.QUEUED)

        # Assert: Schedule should be in datastore
        schedule_db = self.mock_ctx.datastores.schedule_store.get_schedule(task_db.schedule_id)
        self.assertIsNotNone(schedule_db)
        self.assertEqual(schedule_db.id, task_db.schedule_id)

        # Assert: schedule should have a deadline
        self.assertIsNotNone(schedule_db.deadline_at)
        self.assertIsNotNone(schedule_db.schedule)

        # Assert: deadline should be in the future, at least later than the
        # grace period
        self.assertGreater(
            schedule_db.deadline_at,
            datetime.now(timezone.utc),
        )

    def test_post_push_schedule_disabled(self):
        # Arrange
        first_item = functions.create_item(
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
        )

        # Act
        first_item_db = self.scheduler.push_item_to_queue(first_item)

        initial_schedule_db = self.mock_ctx.datastores.schedule_store.get_schedule(first_item_db.schedule_id)

        # Pop
        self.scheduler.pop_item_from_queue()

        # Disable this schedule
        initial_schedule_db.enabled = False
        self.mock_ctx.datastores.schedule_store.update_schedule(
            initial_schedule_db,
        )

        # Act
        second_item = first_item_db.model_copy()
        second_item.id = uuid.uuid4()
        second_item_db = self.scheduler.push_item_to_queue(second_item)

        with capture_logs() as cm:
            self.scheduler.post_push(second_item_db)

        self.assertIn("is disabled, not updating deadline", cm[-1].get("event"))

    def test_post_push_schedule_update_schedule(self):
        # Arrange
        first_item = functions.create_item(
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
        )

        # Act
        first_item_db = self.scheduler.push_item_to_queue(first_item)

        initial_schedule_db = self.mock_ctx.datastores.schedule_store.get_schedule(first_item_db.schedule_id)

        # Pop
        self.scheduler.pop_item_from_queue()

        # Act
        second_item = first_item_db.model_copy()
        second_item.id = uuid.uuid4()
        second_item_db = self.scheduler.push_item_to_queue(second_item)

        updated_schedule_db = self.mock_ctx.datastores.schedule_store.get_schedule(second_item_db.schedule_id)

        # Assert
        self.assertEqual(initial_schedule_db.id, updated_schedule_db.id)
        self.assertNotEqual(updated_schedule_db.deadline_at, initial_schedule_db.deadline_at)

        # There should be only one schedule
        schedules, _ = self.mock_ctx.datastores.schedule_store.get_schedules(scheduler_id=self.scheduler.scheduler_id)

        self.assertEqual(1, len(schedules))

    def test_post_pop(self):
        """When a task is popped from the queue, it should be removed from the database"""
        # Arrange
        item = functions.create_item(
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
            task=functions.create_task(self.scheduler.scheduler_id),
        )

        # Act
        self.scheduler.push_item_to_queue(item)

        # Assert: task should be on priority queue
        pq_item = self.scheduler.queue.peek(0)
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(pq_item.id, item.id)

        # Assert: task should be in datastore, and queued
        task_db = self.mock_ctx.datastores.task_store.get_task(str(item.id))
        self.assertEqual(task_db.id, item.id)
        self.assertEqual(task_db.status, models.TaskStatus.QUEUED)

        # Act
        self.scheduler.pop_item_from_queue()

        # Assert: task should be in datastore, and dispatched
        self.assertEqual(0, self.scheduler.queue.qsize())
        task_db = self.mock_ctx.datastores.task_store.get_task(str(item.id))
        self.assertEqual(task_db.id, item.id)
        self.assertEqual(task_db.status, models.TaskStatus.DISPATCHED)

    def test_disable_scheduler(self):
        # Arrange: start scheduler
        self.scheduler.run()

        # Arrange: add tasks
        item = functions.create_item(
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
        )
        self.scheduler.push_item_to_queue(item)

        # Assert: task should be on priority queue
        pq_item = self.scheduler.queue.peek(0)
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(pq_item.id, item.id)

        # Assert: task should be in datastore, and queued
        task_db = self.mock_ctx.datastores.task_store.get_task(str(item.id))
        self.assertEqual(task_db.id, item.id)
        self.assertEqual(task_db.status, models.TaskStatus.QUEUED)

        # Assert: listeners should be running
        self.assertGreater(len(self.scheduler.listeners), 0)

        # Assert: threads should be running
        self.assertGreater(len(self.scheduler.threads), 0)

        # Act
        self.scheduler.disable()

        # Listeners should be stopped
        self.assertEqual(0, len(self.scheduler.listeners))

        # Threads should be stopped
        self.assertEqual(0, len(self.scheduler.threads))

        # Queue should be empty
        self.assertEqual(0, self.scheduler.queue.qsize())

        # All tasks on queue should be set to CANCELLED
        tasks, _ = self.mock_ctx.datastores.task_store.get_tasks(self.scheduler.scheduler_id)
        for task in tasks:
            self.assertEqual(task.status, models.TaskStatus.CANCELLED)

        # Scheduler should be disabled
        self.assertFalse(self.scheduler.is_enabled())

        with self.assertRaises(queues.errors.NotAllowedError):
            self.scheduler.push_item_to_queue(item)

    def test_enable_scheduler(self):
        # Arrange: start scheduler
        self.scheduler.run()

        # Arrange: add tasks
        item = functions.create_item(
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
        )
        self.scheduler.push_item_to_queue(item)

        # Assert: listeners should be running
        self.assertGreater(len(self.scheduler.listeners), 0)

        # Assert: threads should be running
        self.assertGreater(len(self.scheduler.threads), 0)

        # Disable scheduler first
        self.scheduler.disable()

        # Listeners should be stopped
        self.assertEqual(0, len(self.scheduler.listeners))

        # Threads should be stopped
        self.assertEqual(0, len(self.scheduler.threads))

        # Queue should be empty
        self.assertEqual(0, self.scheduler.queue.qsize())

        # All tasks on queue should be set to CANCELLED
        tasks, _ = self.mock_ctx.datastores.task_store.get_tasks(self.scheduler.scheduler_id)
        for task in tasks:
            self.assertEqual(task.status, models.TaskStatus.CANCELLED)

        # Re-enable scheduler
        self.scheduler.enable()

        # Threads should be started
        self.assertGreater(len(self.scheduler.threads), 0)

        # Scheduler should be enabled
        self.assertTrue(self.scheduler.is_enabled())

        # Push item to the queue
        self.scheduler.push_item_to_queue(item)

        # Assert: task should be on priority queue
        pq_item = self.scheduler.queue.peek(0)
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(pq_item.id, item.id)

        # Stop the scheduler
        self.scheduler.stop()
