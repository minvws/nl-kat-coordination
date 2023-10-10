import unittest
from types import SimpleNamespace
from unittest import mock

import scheduler
from fastapi.testclient import TestClient
from scheduler import config, models, server, storage

from tests.factories import OrganisationFactory
from tests.mocks import MockKatalogusService


class AppTestCase(unittest.TestCase):
    def setUp(self):
        # Application Context
        self.mock_ctx = mock.patch("scheduler.context.AppContext").start()
        self.mock_ctx.config = config.settings.Settings()
        self.mock_ctx.services.katalogus = MockKatalogusService()

        # Database
        self.dbconn = storage.DBConn(str(self.mock_ctx.config.db_uri))
        models.Base.metadata.create_all(self.dbconn.engine)
        self.mock_ctx.datastores = SimpleNamespace(
            **{
                storage.TaskStore.name: storage.TaskStore(self.dbconn),
                storage.PriorityQueueStore.name: storage.PriorityQueueStore(self.dbconn),
            }
        )

        # App
        self.app = scheduler.App(self.mock_ctx)
        self.app.server = server.Server(self.mock_ctx, self.app.schedulers)

        # Test client
        self.client = TestClient(self.app.server.api)

    def tearDown(self):
        self.app.shutdown()
        models.Base.metadata.drop_all(self.dbconn.engine)
        self.dbconn.engine.dispose()

    def test_monitor_orgs_add(self):
        """Test that when a new organisation is added, a new scheduler is created"""
        # Arrange
        self.mock_ctx.services.katalogus.organisations = {
            "org-1": OrganisationFactory(id="org-1"),
            "org-2": OrganisationFactory(id="org-2"),
        }

        # Act
        self.app.monitor_organisations()

        # Assert: four schedulers should have been created for two organisations
        self.assertEqual(4, len(self.app.schedulers.keys()))
        self.assertEqual(4, len(self.app.server.schedulers.keys()))

        scheduler_org_ids = {s.organisation.id for s in self.app.schedulers.values()}
        self.assertEqual({"org-1", "org-2"}, scheduler_org_ids)

    def test_monitor_orgs_remove(self):
        """Test that when an organisation is removed, the scheduler is removed"""
        # Arrange
        self.mock_ctx.services.katalogus.organisations = {
            "org-1": OrganisationFactory(id="org-1"),
            "org-2": OrganisationFactory(id="org-2"),
        }

        # Act
        self.app.monitor_organisations()

        # Assert: four schedulers should have been created for two organisations
        self.assertEqual(4, len(self.app.schedulers.keys()))
        self.assertEqual(4, len(self.app.server.schedulers.keys()))

        scheduler_org_ids = {s.organisation.id for s in self.app.schedulers.values()}
        self.assertEqual({"org-1", "org-2"}, scheduler_org_ids)

        # Arrange
        self.mock_ctx.services.katalogus.organisations = {}

        # Act
        self.app.monitor_organisations()

        # Assert
        self.assertEqual(0, len(self.app.schedulers.keys()))
        self.assertEqual(0, len(self.app.server.schedulers.keys()))

        scheduler_org_ids = {s.organisation.id for s in self.app.schedulers.values()}
        self.assertEqual(set(), scheduler_org_ids)

    def test_monitor_orgs_add_and_remove(self):
        """Test that when an organisation is added and removed, the scheduler
        is removed"""
        # Arrange
        self.mock_ctx.services.katalogus.organisations = {
            "org-1": OrganisationFactory(id="org-1"),
            "org-2": OrganisationFactory(id="org-2"),
        }

        # Act
        self.app.monitor_organisations()

        # Assert: four schedulers should have been created for two organisations
        self.assertEqual(4, len(self.app.schedulers.keys()))
        self.assertEqual(4, len(self.app.server.schedulers.keys()))

        scheduler_org_ids = {s.organisation.id for s in self.app.schedulers.values()}
        self.assertEqual({"org-1", "org-2"}, scheduler_org_ids)

        # Arrange
        self.mock_ctx.services.katalogus.organisations = {
            "org-1": OrganisationFactory(id="org-1"),
            "org-3": OrganisationFactory(id="org-3"),
        }

        # Act
        self.app.monitor_organisations()

        # Assert
        self.assertEqual(4, len(self.app.schedulers.keys()))
        self.assertEqual(4, len(self.app.server.schedulers.keys()))

        scheduler_org_ids = {s.organisation.id for s in self.app.schedulers.values()}
        self.assertEqual({"org-1", "org-3"}, scheduler_org_ids)
