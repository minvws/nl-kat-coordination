import unittest
from unittest import mock

import scheduler
from scheduler import config, models, repositories
from tests.factories import OrganisationFactory


class AppTestCase(unittest.TestCase):
    def setUp(self):
        cfg = config.settings.Settings()

        self.mock_ctx = mock.patch("scheduler.context.AppContext").start()
        self.mock_ctx.config = cfg

        # Datastore
        self.mock_ctx.datastore = repositories.sqlalchemy.SQLAlchemy("sqlite:///")
        models.Base.metadata.create_all(self.mock_ctx.datastore.engine)

        self.pq_store = repositories.sqlalchemy.PriorityQueueStore(self.mock_ctx.datastore)
        self.task_store = repositories.sqlalchemy.TaskStore(self.mock_ctx.datastore)

        self.mock_ctx.pq_store = self.pq_store
        self.mock_ctx.task_store = self.task_store

        self.organisation = OrganisationFactory()

        self.app = scheduler.App(self.mock_ctx)

    @mock.patch("scheduler.context.AppContext.services.katalogus.get_organisations")
    @mock.patch("scheduler.context.AppContext.services.katalogus.get_organisation")
    def test_monitor_orgs_add(self, mock_get_organisation, mock_get_organisations):
        """Test that when a new organisation is added, a new scheduler is created"""
        mock_get_organisations.return_value = [self.organisation]
        mock_get_organisation.return_value = self.organisation

        # Two schedulers should have been created
        self.app.monitor_organisations()
        self.assertEqual(2, len(self.app.schedulers.keys()))

    @mock.patch("scheduler.context.AppContext.services.katalogus.get_organisations")
    @mock.patch("scheduler.context.AppContext.services.katalogus.get_organisation")
    def test_monitor_orgs_remove(self, mock_get_organisation, mock_get_organisations):
        """Test that when an organisation is removed, the scheduler is removed"""

        mock_get_organisations.return_value = [self.organisation]
        mock_get_organisation.return_value = self.organisation

        # Two schedulers should have been created
        self.app.monitor_organisations()
        self.assertEqual(2, len(self.app.schedulers.keys()))

        mock_get_organisations.return_value = []
        mock_get_organisation.return_value = None

        # Two schedulers should have been removed
        self.app.monitor_organisations()
        self.assertEqual(0, len(self.app.schedulers.keys()))
