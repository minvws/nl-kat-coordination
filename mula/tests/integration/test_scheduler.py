import unittest
from unittest import mock

from scheduler import config, models, repositories

from tests.mocks import queue as mock_queue
from tests.mocks import ranker as mock_ranker
from tests.mocks import scheduler as mock_scheduler
from tests.mocks import task as mock_task
from tests.utils import functions


class SchedulerTestCase(unittest.TestCase):
    def setUp(self):
        cfg = config.settings.Settings()

        self.mock_ctx = mock.patch("scheduler.context.AppContext").start()
        self.mock_ctx.config = cfg

        self.mock_ctx.datastore = repositories.sqlalchemy.SQLAlchemy(cfg.database_dsn)
        models.Base.metadata.create_all(self.mock_ctx.datastore.engine)

        self.pq_store = repositories.sqlalchemy.PriorityQueueStore(self.mock_ctx.datastore)

        queue = mock_queue.MockPriorityQueue(
            pq_id="test",
            maxsize=cfg.pq_maxsize,
            item_type=mock_task.MockTask,
            allow_priority_updates=True,
            pq_store=self.pq_store,
        )

        ranker = mock_ranker.MockRanker(
            ctx=self.mock_ctx,
        )

        self.scheduler = mock_scheduler.MockScheduler(
            ctx=self.mock_ctx,
            scheduler_id="test",
            queue=queue,
            ranker=ranker,
        )

    def test_post_push(self):
        """When a task is added to the queue, it should be added to the database"""
        # Arrange
        mock_task.MockTask()

        p_item = functions.create_p_item(
            scheduler_id=self.scheduler.scheduler_id,
            priority=0,
        )

        # Act
        self.scheduler.push_item_to_queue(p_item)

        # Task should be on priority queue
        task_pq = mock_task.MockTask(**self.scheduler.queue.peek(0).data)
        self.assertEqual(1, self.scheduler.queue.qsize())
        self.assertEqual(task_pq.id, p_item.id)
        self.assertEqual(task_pq.status, models.TaskStatus.QUEUED.name)

        # Task should be in datastore, and queued
        task_db = self.mock_ctx.task_store.get_task_by_id(p_item.id)
        self.assertEqual(task_db.id, p_item.id)
        self.assertEqual(task_db.status, models.TaskStatus.QUEUED)
