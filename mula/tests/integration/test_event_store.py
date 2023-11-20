import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest import mock

from scheduler import config, models, storage

from tests.factories import OrganisationFactory
from tests.utils import functions


class EventStoreTestCase(unittest.TestCase):
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
                storage.EventStore.name: storage.EventStore(self.dbconn),
            }
        )

        models.TaskDB.set_event_store(self.mock_ctx.datastores.event_store)

        # Organisation
        self.organisation = OrganisationFactory()

    def tearDown(self):
        models.Base.metadata.drop_all(self.dbconn.engine)
        self.dbconn.engine.dispose()

    def test_get_task_duration(self):
        # Arrange
        p_item = functions.create_p_item(self.organisation.id, 1)
        task = functions.create_task(p_item)
        self.mock_ctx.datastores.task_store.create_task(task)

        task.status = models.TaskStatus.COMPLETED
        task.modified_at = datetime.now() + timedelta(seconds=60)
        self.mock_ctx.datastores.task_store.update_task(task)

        task_db = self.mock_ctx.datastores.task_store.get_task_by_id(task.id)
        print(task_db)
        breakpoint()

    def test_get_task_runtime(self):
        pass

    def test_get_task_queued(self):
        pass
