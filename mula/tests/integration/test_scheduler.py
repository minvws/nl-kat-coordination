import unittest
import uuid
from types import SimpleNamespace
from unittest import mock

from scheduler import config, models, queues, storage
from tests.mocks import queue as mock_queue
from tests.mocks import scheduler as mock_scheduler
from tests.mocks import task as mock_task
from tests.utils import functions


class SchedulerTestCase(unittest.TestCase):
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
                storage.PriorityQueueStore.name: storage.PriorityQueueStore(self.dbconn),
                storage.SchemaStore.name: storage.SchemaStore(self.dbconn),
            }
        )

        identifier = uuid.uuid4().hex

        queue = mock_queue.MockPriorityQueue(
            pq_id=identifier,
            maxsize=self.mock_ctx.config.pq_maxsize,
            item_type=mock_task.MockTask,
            allow_priority_updates=True,
            pq_store=self.mock_ctx.datastores.pq_store,
        )

        self.scheduler = mock_scheduler.MockScheduler(
            ctx=self.mock_ctx,
            scheduler_id=identifier,
            queue=queue,
        )

    def tearDown(self):
        self.scheduler.stop()
        models.Base.metadata.drop_all(self.dbconn.engine)
        self.dbconn.engine.dispose()

    def test_push_items_to_queue(self):
        pass

    def test_push_item_to_queue(self):
        pass

    def test_push_item_to_queue_with_timeout(self):
        pass

    def test_push_item_to_queue_full(self):
        pass

    def test_push_item_to_queue_invalid(self):
        pass

    def test_push_item_to_queue_not_allowed(self):
        pass

    def test_pop_item_from_queue(self):
        pass

    def test_pop_item_from_queue_empty(self):
        pass

    def test_post_push(self):
        """When a task is added to the queue, it should be added to the database"""
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
        schedule_db = self.mock_ctx.datastores.schema_store.get_schema(task_db.schema_id)
        self.assertEqual(schedule_db.id, task_db.schema_id)

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
        popped_item = self.scheduler.pop_item_from_queue()

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

    @unittest.skip("refactor")
    def test_signal_handler_task_not_finished(self):
        # Arrange
        item = functions.create_item(
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
        )

        self.scheduler.push_item_to_queue(item)

        task_db = self.mock_ctx.datastores.task_store.get_task(str(item.id))

        # Get schedule
        initial_schedule_db = self.mock_ctx.datastores.schema_store.get_schema(task_db.schema_id)
        initial_timestamp = initial_schedule_db.deadline_at

        self.scheduler.signal_handler_task(task_db)

        # Assert: schedule should have same deadline
        updated_schedule_db = self.mock_ctx.datastores.schema_store.get_schema(task_db.schema_id)
        updated_timestamp = updated_schedule_db.deadline_at
        self.assertEqual(initial_timestamp, updated_timestamp)

    @unittest.skip("refactor")
    def test_signal_handler_malformed_cron_expression(self):
        # Arrange
        item = functions.create_item(
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
        )

        self.scheduler.push_item_to_queue(item)
        self.scheduler.pop_item_from_queue()

        task_db = self.mock_ctx.datastores.task_store.get_task(str(item.id))

        # Get schedule
        initial_schedule_db = self.mock_ctx.datastores.schema_store.get_schema(task_db.schema_id)

        # Set cron expression to malformed
        with self.assertRaises(ValueError):
            initial_schedule_db.schedule = ".&^%$#"
