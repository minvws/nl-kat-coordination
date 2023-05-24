import unittest
from unittest import mock

import scheduler
from fastapi.testclient import TestClient
from scheduler import config, models, repositories, server

from tests.factories import OrganisationFactory


class AppTestCase(unittest.TestCase):
    def setUp(self):
        cfg = config.settings.Settings()

        self.mock_ctx = mock.patch("scheduler.context.AppContext").start()
        self.mock_ctx.config = cfg

        # Datastore
        self.mock_ctx.datastore = repositories.sqlalchemy.SQLAlchemy(cfg.database_dsn)
        models.Base.metadata.create_all(self.mock_ctx.datastore.engine)

        self.pq_store = repositories.sqlalchemy.PriorityQueueStore(self.mock_ctx.datastore)
        self.task_store = repositories.sqlalchemy.TaskStore(self.mock_ctx.datastore)

        self.mock_ctx.pq_store = self.pq_store
        self.mock_ctx.task_store = self.task_store

        self.organisation = OrganisationFactory()

        self.app = scheduler.App(self.mock_ctx)

        self.app.server = server.Server(self.mock_ctx, self.app.schedulers)

        self.client = TestClient(self.app.server.api)

    @mock.patch("scheduler.context.AppContext.services.katalogus.get_organisations")
    @mock.patch("scheduler.context.AppContext.services.katalogus.get_organisation")
    def test_monitor_orgs_add(self, mock_get_organisation, mock_get_organisations):
        """Test that when a new organisation is added, a new scheduler is created"""
        # Arrange
        mock_get_organisations.return_value = [self.organisation]
        mock_get_organisation.return_value = self.organisation

        # Act
        self.app.monitor_organisations()

        # Assert: two schedulers should have been created
        self.assertEqual(2, len(self.app.schedulers.keys()))
        self.assertEqual(2, len(self.app.server.schedulers.keys()))

        response = self.client.get("/schedulers")
        self.assertEqual(2, len(response.json()))

        self.app.shutdown()

    @mock.patch("scheduler.context.AppContext.services.katalogus.get_organisations")
    @mock.patch("scheduler.context.AppContext.services.katalogus.get_organisation")
    def test_monitor_orgs_remove(self, mock_get_organisation, mock_get_organisations):
        """Test that when an organisation is removed, the scheduler is removed"""
        # Arrange
        mock_get_organisations.return_value = [self.organisation]
        mock_get_organisation.return_value = self.organisation

        # Act
        self.app.monitor_organisations()

        # Assert: two schedulers should have been created
        self.assertEqual(2, len(self.app.schedulers.keys()))

        response = self.client.get("/schedulers")
        self.assertEqual(2, len(response.json()))

        response = self.client.get("/queues")
        self.assertEqual(2, len(response.json()))

        # Arrange
        mock_get_organisations.return_value = []
        mock_get_organisation.return_value = None

        # Act
        self.app.monitor_organisations()

        # Assert
        self.assertEqual(0, len(self.app.schedulers.keys()))
        self.assertEqual(0, len(self.app.server.schedulers.keys()))

        response = self.client.get("/schedulers")
        self.assertEqual(0, len(response.json()))
        self.assertEqual([], response.json())

        response = self.client.get("/queues")
        self.assertEqual(0, len(response.json()))
        self.assertEqual([], response.json())

    # @unittest.skip("TODO: fix this test")
    @mock.patch("scheduler.context.AppContext.services.katalogus.get_organisations")
    @mock.patch("scheduler.context.AppContext.services.katalogus.get_organisation")
    @mock.patch("scheduler.schedulers.BoefjeScheduler.push_tasks_for_new_boefjes")
    def test_unhandled_exception(self, mock_run, mock_get_organisation, mock_get_organisations):
        """Test that an unhandled exception results is logged and that the
        application is being stopped"""
        # Mocks
        mock_get_organisations.return_value = [self.organisation]
        mock_get_organisation.return_value = self.organisation
        mock_run.side_effect = Exception("Test")

        # Act
        self.app.run()
