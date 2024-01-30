import unittest
from types import SimpleNamespace
from unittest import mock

from scheduler import config, models, rankers, storage


class DefaultDeadlineRanker(unittest.TestCase):
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
                storage.ScheduleStore.name: storage.ScheduleStore(self.dbconn),
            }
        )

        self.ranker = rankers.DefaultDeadlineRanker(self.mock_ctx)

    def tearDown(self):
        models.Base.metadata.drop_all(self.dbconn.engine)
        self.dbconn.engine.dispose()

    def test_calculate_deadline(self):
        deadline = self.ranker.rank(None)
        self.assertIsNotNone(deadline)

    def test_calculate_deadline_cron(self):
        schedule = models.Schedule(
            scheduler_id="test",
            p_item=models.PrioritizedItem(hash="test", priority=1),
            cron_expression="0 12 * * 1",  # every Monday at noon
        )

        deadline = self.ranker.rank(schedule)
        self.assertIsNotNone(deadline)

    def test_calculate_deadline_malformed(self):
        schedule = models.Schedule(
            scheduler_id="test",
            p_item=models.PrioritizedItem(hash="test", priority=1),
            cron_expression=".&^%$#",
        )

        with self.assertRaises(ValueError):
            self.ranker.rank(schedule)
