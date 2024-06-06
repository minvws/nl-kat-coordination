import os
from unittest import TestCase, skipIf

import alembic.config
from sqlalchemy.orm import sessionmaker

from boefjes.config import settings
from boefjes.katalogus.models import Boefje, Organisation
from boefjes.katalogus.storage.interfaces import OrganisationNotFound, PluginNotFound, SettingsNotFound, StorageError
from boefjes.sql.db import SQL_BASE, get_engine
from boefjes.sql.organisation_storage import SQLOrganisationStorage
from boefjes.sql.plugin_enabled_storage import SQLPluginEnabledStorage
from boefjes.sql.setting_storage import SQLSettingsStorage, create_encrypter


@skipIf(os.environ.get("CI") != "1", "Needs a CI database.")
class TestRepositories(TestCase):
    def setUp(self) -> None:
        alembic.config.main(argv=["--config", "/app/boefjes/boefjes/alembic.ini", "upgrade", "head"])

        session = sessionmaker(bind=get_engine())()
        self.organisation_storage = SQLOrganisationStorage(session, settings)
        self.settings_storage = SQLSettingsStorage(session, create_encrypter())
        self.plugin_state_storage = SQLPluginEnabledStorage(session, settings)

    def tearDown(self) -> None:
        session = sessionmaker(bind=get_engine())()

        for table in SQL_BASE.metadata.tables:
            session.execute(f"DELETE FROM {table} CASCADE")  # noqa: S608

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

    def test_organisations(self):
        org = Organisation(id="org1", name="Test")

        with self.organisation_storage as storage:
            storage.create(org)

        returned_org = storage.get_by_id(org.id)
        self.assertEqual(org, returned_org)

    def test_settings_storage(self):
        organisation_id = "test"
        plugin_id = 64 * "a"

        org = Organisation(id=organisation_id, name="Test")
        with self.organisation_storage as storage:
            storage.create(org)

        with self.settings_storage as settings_storage:
            settings_storage.upsert({"TEST_SETTING": "123.9", "TEST_SETTING2": 12}, organisation_id, plugin_id)

        with self.settings_storage as settings_storage:
            settings_storage.upsert({"TEST_SETTING": "123.9", "TEST_SETTING2": 13}, organisation_id, plugin_id)

        returned_settings = settings_storage.get_all(organisation_id, plugin_id)
        self.assertEqual("123.9", returned_settings["TEST_SETTING"])
        self.assertEqual(13, returned_settings["TEST_SETTING2"])

        with self.assertRaises(SettingsNotFound):
            settings_storage.delete("no organisation!", plugin_id)

        self.assertEqual({"TEST_SETTING": "123.9", "TEST_SETTING2": 13}, settings_storage.get_all(org.id, plugin_id))
        self.assertEqual(dict(), settings_storage.get_all(org.id, "wrong"))
        self.assertEqual(dict(), settings_storage.get_all("wrong", plugin_id))

        with self.settings_storage as settings_storage:
            settings_storage.delete(org.id, plugin_id)

        self.assertEqual(dict(), settings_storage.get_all(org.id, plugin_id))

        with self.assertRaises(StorageError), self.settings_storage as settings_storage:
            settings_storage.upsert({"TEST_SETTING": "123.9"}, organisation_id, 65 * "a")

    def test_settings_storage_values_field_limits(self):
        organisation_id = "test"
        plugin_id = 64 * "a"

        org = Organisation(id=organisation_id, name="Test")
        with self.organisation_storage as storage:
            storage.create(org)

        with self.settings_storage as settings_storage:
            settings_storage.upsert(
                {
                    "TEST_SETTING": 12 * "123.9",
                    "TEST_SETTING2": 12000,
                    "TEST_SETTING3": 30 * "b",
                    "TEST_SETTING4": 30 * "b",
                    "TEST_SETTING5": 10 * "b",
                    "TEST_SETTING6": 123456789,
                },
                organisation_id,
                plugin_id,
            )

        self.assertEqual(
            {
                "TEST_SETTING": 12 * "123.9",
                "TEST_SETTING2": 12000,
                "TEST_SETTING3": 30 * "b",
                "TEST_SETTING4": 30 * "b",
                "TEST_SETTING5": 10 * "b",
                "TEST_SETTING6": 123456789,
            },
            settings_storage.get_all(org.id, plugin_id),
        )

    def test_plugin_enabled_storage(self):
        with self.organisation_storage as storage:
            org = Organisation(id="test", name="Test")
            storage.create(org)

        with self.plugin_state_storage as plugin_state_storage:
            plugin = Boefje(
                id="test-boefje-1",
                name="Test Boefje 1",
                version="0.1",
                consumes={"WebPage"},
                produces=["text/html"],
                enabled=True,
            )
            plugin_state_storage.create(plugin.id, plugin.enabled, org.id)

        returned_state = plugin_state_storage.get_by_id(plugin.id, org.id)
        self.assertTrue(returned_state)

        with self.plugin_state_storage as plugin_state_storage:
            plugin_state_storage.update_or_create_by_id(plugin.id, False, org.id)

        returned_state = plugin_state_storage.get_by_id(plugin.id, org.id)
        self.assertFalse(returned_state)

        with self.assertRaises(PluginNotFound):
            plugin_state_storage.get_by_id("wrong", org.id)

        with self.assertRaises(PluginNotFound):
            plugin_state_storage.get_by_id("wrong", org.id)

        with self.assertRaises(PluginNotFound):
            plugin_state_storage.get_by_id(plugin.id, "wrong")
