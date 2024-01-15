import unittest
from types import SimpleNamespace
from unittest import mock

from scheduler import config, models, queues, rankers, storage


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
                storage.JobStore.name: storage.JobStore(self.dbconn),
            }
        )

        self.ranker = rankers.DefaultDeadlineRanker(self.mock_ctx)

    def tearDown(self):
        models.Base.metadata.drop_all(self.dbconn.engine)
        self.dbconn.engine.dispose()

    def test_calculate_deadline(self):
        self.ranker.rank(None)
