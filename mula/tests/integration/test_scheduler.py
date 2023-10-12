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
        cfg = config.settings.Settings()

        # Database
        self.dbconn = storage.DBConn(str(cfg.db_uri))
        models.Base.metadata.create_all(self.dbconn.engine)
        self.mock_ctx.datastores = SimpleNamespace(
            **{
                storage.TaskStore.name: storage.TaskStore(self.dbconn),
                storage.PriorityQueueStore.name: storage.PriorityQueueStore(self.dbconn),
            }
        )

        identifier = uuid.uuid4().hex

        queue = mock_queue.MockPriorityQueue(
            pq_id=identifier,
            maxsize=cfg.pq_maxsize,
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

    def test_post_push(self):
        """When a task is added to the queue, it should be added to the database"""
        # Arrange
        p_item = functions.create_p_item(
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
        )

        # Act
        self.scheduler.push_item_to_queue(p_item)

        # Task should be on priority queue
        pq_p_item = self.scheduler.queue.peek(0)
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(pq_p_item.id, p_item.id)

        # Task should be in datastore, and queued
        task_db = self.mock_ctx.datastores.task_store.get_task_by_id(p_item.id)
        self.assertEqual(task_db.id, p_item.id)
        self.assertEqual(task_db.status, models.TaskStatus.QUEUED)

    def test_post_pop(self):
        """When a task is popped from the queue, it should be removed from the database"""
        # Arrange
        p_item = functions.create_p_item(
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
        )

        # Act
        self.scheduler.push_item_to_queue(p_item)

        # Assert: task should be on priority queue
        pq_p_item = self.scheduler.queue.peek(0)
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(pq_p_item.id, p_item.id)

        # Assert: task should be in datastore, and queued
        task_db = self.mock_ctx.datastores.task_store.get_task_by_id(p_item.id)
        self.assertEqual(task_db.id, p_item.id)
        self.assertEqual(task_db.status, models.TaskStatus.QUEUED)

        # Act
        self.scheduler.pop_item_from_queue()

        # Assert: task should be in datastore, and dispatched
        self.assertEqual(0, self.scheduler.queue.qsize())
        task_db = self.mock_ctx.datastores.task_store.get_task_by_id(p_item.id)
        self.assertEqual(task_db.id, p_item.id)
        self.assertEqual(task_db.status, models.TaskStatus.DISPATCHED)

    def test_disable_scheduler(self):
        # Arrange: start scheduler
        self.scheduler.run()

        # Arrange: add tasks
        p_item = functions.create_p_item(
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
        )
        self.scheduler.push_item_to_queue(p_item)

        # Assert: task should be on priority queue
        pq_p_item = self.scheduler.queue.peek(0)
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(pq_p_item.id, p_item.id)

        # Assert: task should be in datastore, and queued
        task_db = self.mock_ctx.datastores.task_store.get_task_by_id(p_item.id)
        self.assertEqual(task_db.id, p_item.id)
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
            self.scheduler.push_item_to_queue(p_item)

    def test_enable_scheduler(self):
        # Arrange: start scheduler
        self.scheduler.run()

        # Arrange: add tasks
        p_item = functions.create_p_item(
            scheduler_id=self.scheduler.scheduler_id,
            priority=1,
        )
        self.scheduler.push_item_to_queue(p_item)

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
        self.scheduler.push_item_to_queue(p_item)

        # Assert: task should be on priority queue
        pq_p_item = self.scheduler.queue.peek(0)
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(pq_p_item.id, p_item.id)

        # Stop the scheduler
        self.scheduler.stop()
