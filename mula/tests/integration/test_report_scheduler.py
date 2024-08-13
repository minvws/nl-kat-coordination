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
        self.scheduler = schedulers.NormalizerScheduler(
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

        self.mock_latest_task_by_hash = mock.patch(
            "scheduler.context.AppContext.datastores.task_store.get_latest_task_by_hash"
        ).start()

        self.mock_get_plugin = mock.patch(
            "scheduler.context.AppContext.services.katalogus.get_plugin_by_id_and_org_id",
        ).start()
