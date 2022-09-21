import os
import time
from unittest import TestCase, skipIf

from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError

from boefjes.config import settings
from boefjes.katalogus.models import Organisation, Repository, Boefje
from boefjes.katalogus.storage.interfaces import (
    OrganisationNotFound,
    PluginNotFound,
    SettingNotFound,
    RepositoryNotFound,
    StorageError,
)
from boefjes.sql.db import get_engine, SQL_BASE
from boefjes.sql.organisation_storage import SQLOrganisationStorage
from boefjes.sql.repository_storage import SQLRepositoryStorage
from boefjes.sql.setting_storage import SQLSettingsStorage
from boefjes.sql.plugin_enabled_storage import SQLPluginEnabledStorage


@skipIf(os.environ.get("CI") != "1", "Needs a CI database.")
class TestRepositories(TestCase):
    def setUp(self) -> None:
        self.engine = get_engine()

        # Some retries to handle db startup time in tests
        for i in range(3):
            try:
                SQL_BASE.metadata.create_all(self.engine)
                break
            except OperationalError as e:
                if i == 2:
                    raise e

                time.sleep(1)

        session = sessionmaker(bind=self.engine)()
        self.organisation_storage = SQLOrganisationStorage(session, settings)
        self.repository_storage = SQLRepositoryStorage(session, settings)
        self.settings_storage = SQLSettingsStorage(session, settings)
        self.plugin_state_storage = SQLPluginEnabledStorage(session, settings)

    def tearDown(self) -> None:
        session = sessionmaker(bind=get_engine())()

        for table in SQL_BASE.metadata.tables.keys():
            session.execute(f"DELETE FROM {table} CASCADE")

        session.commit()
        session.close()

    def test_organisation_storage(self):
        organisation_id = "test"

        org = Organisation(id=organisation_id, name="Test")
        with self.organisation_storage as storage:
            storage.create(org)

        returned_org = storage.get_by_id(organisation_id)
        self.assertEqual(org, returned_org)

        all_organisations = storage.get_all()
        self.assertEqual(org, all_organisations[organisation_id])

        with self.organisation_storage as storage:
            storage.delete_by_id(organisation_id)

        with self.assertRaises(OrganisationNotFound):
            storage.get_by_id(organisation_id)

    def test_repository_storage(self):
        repository_id = "test"

        with self.repository_storage as repository_storage:
            repo = Repository(
                id=repository_id,
                name="Test",
                base_url="http://test.url",
            )
            repository_storage.create(repo)

        returned_repo = repository_storage.get_by_id(repository_id)
        self.assertEqual(repo, returned_repo)

        all_repositories = repository_storage.get_all()
        self.assertEqual(repo, all_repositories[repository_id])

        with self.assertRaises(RepositoryNotFound):
            repository_storage.get_by_id("wrong_id")

    def test_organisations_repositories(self):
        org = Organisation(id="org1", name="Test")
        repo = Repository(
            id="repo-123",
            name="Test",
            base_url="http://test.url",
        )

        with self.repository_storage as storage:
            storage.create(repo)

        with self.organisation_storage as storage:
            storage.create(org)
            storage.add_repository(org.id, repo.id)

        returned_org = storage.get_by_id(org.id)
        self.assertEqual(org, returned_org)

        repositories = storage.get_repositories(org.id)
        self.assertEqual(1, len(repositories))
        self.assertEqual(repo, repositories[0])

        repo2 = Repository(
            id="repo-321",
            name="Test",
            base_url="http://test.url",
        )

        with self.repository_storage as storage:
            storage.create(repo2)

        with self.organisation_storage as storage:
            storage.add_repository(org.id, repo2.id)

        repositories = storage.get_repositories(org.id)
        self.assertEqual(2, len(repositories))
        self.assertEqual(repo2, repositories[1])

    def test_settings_storage(self):
        organisation_id = "test"
        plugin_id = 64 * "a"

        org = Organisation(id=organisation_id, name="Test")
        with self.organisation_storage as storage:
            storage.create(org)

        with self.settings_storage as settings_storage:
            settings_storage.create("TEST_SETTING", "123.9", organisation_id, plugin_id)

        returned_settings = settings_storage.get_by_key(
            "TEST_SETTING", organisation_id, plugin_id
        )
        self.assertEqual("123.9", returned_settings)

        with self.assertRaises(SettingNotFound):
            settings_storage.get_by_key("no setting!", organisation_id, plugin_id)

        with self.assertRaises(SettingNotFound):
            settings_storage.get_by_key("TEST_SETTING", "no organisation!", plugin_id)

        self.assertEqual(
            {"TEST_SETTING": "123.9"}, settings_storage.get_all(org.id, plugin_id)
        )
        self.assertEqual(dict(), settings_storage.get_all(org.id, "wrong"))
        self.assertEqual(dict(), settings_storage.get_all("wrong", plugin_id))

        with self.settings_storage as settings_storage:
            settings_storage.delete_by_key("TEST_SETTING", org.id, plugin_id)

        self.assertEqual(dict(), settings_storage.get_all(org.id, plugin_id))

        with self.assertRaises(StorageError):
            with self.settings_storage as settings_storage:
                settings_storage.create(
                    "TEST_SETTING", "123.9", organisation_id, 65 * "a"
                )

    def test_plugin_enabled_storage(self):
        with self.organisation_storage as storage:
            org = Organisation(id="test", name="Test")
            storage.create(org)

        with self.repository_storage as storage:
            repo = Repository(
                id="repo-test",
                name="Test",
                base_url="http://test.url",
            )
            storage.create(repo)

        with self.plugin_state_storage as plugin_state_storage:
            plugin = Boefje(
                id="test-boefje-1",
                name="Test Boefje 1",
                repository_id=repo.id,
                version="0.1",
                consumes={"WebPage"},
                produces=["text/html"],
                enabled=True,
            )
            plugin_state_storage.create(
                plugin.id, plugin.repository_id, plugin.enabled, org.id
            )

        returned_state = plugin_state_storage.get_by_id(plugin.id, repo.id, org.id)
        self.assertTrue(returned_state)

        with self.plugin_state_storage as plugin_state_storage:
            plugin_state_storage.update_or_create_by_id(
                plugin.id, repo.id, False, org.id
            )

        returned_state = plugin_state_storage.get_by_id(plugin.id, repo.id, org.id)
        self.assertFalse(returned_state)

        with self.assertRaises(PluginNotFound):
            plugin_state_storage.get_by_id("wrong", repo.id, org.id)

        with self.assertRaises(PluginNotFound):
            plugin_state_storage.get_by_id(plugin.id, "wrong", org.id)

        with self.assertRaises(PluginNotFound):
            plugin_state_storage.get_by_id(plugin.id, repo.id, "wrong")
