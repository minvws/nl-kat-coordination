import datetime
import os
from unittest import TestCase, skipIf

import alembic.config
from sqlalchemy.orm import sessionmaker

from boefjes.config import settings
from boefjes.models import Boefje, Normalizer, Organisation
from boefjes.sql.db import SQL_BASE, get_engine
from boefjes.sql.organisation_storage import SQLOrganisationStorage
from boefjes.sql.plugin_enabled_storage import SQLPluginEnabledStorage
from boefjes.sql.plugin_storage import SQLPluginStorage
from boefjes.sql.setting_storage import SQLSettingsStorage, create_encrypter
from boefjes.storage.interfaces import (
    OrganisationNotFound,
    PluginNotFound,
    PluginStateNotFound,
    SettingsNotFound,
    StorageError,
)


@skipIf(os.environ.get("CI") != "1", "Needs a CI database.")
class TestRepositories(TestCase):
    def setUp(self) -> None:
        alembic.config.main(argv=["--config", "/app/boefjes/boefjes/alembic.ini", "upgrade", "head"])

        session = sessionmaker(bind=get_engine())()
        self.organisation_storage = SQLOrganisationStorage(session, settings)
        self.settings_storage = SQLSettingsStorage(session, create_encrypter())
        self.plugin_state_storage = SQLPluginEnabledStorage(session, settings)
        self.plugin_storage = SQLPluginStorage(session, settings)

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

    def test_settings_storage(self):
        organisation_id = "test"
        plugin_id = 64 * "a"

        with self.plugin_storage as storage:
            storage.create_boefje(Boefje(id=plugin_id, name="Test"))

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

        with self.plugin_storage as storage:
            storage.create_boefje(Boefje(id=plugin_id, name="Test"))

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

        with self.assertRaises(PluginStateNotFound):
            plugin_state_storage.get_by_id("wrong", org.id)

        with self.assertRaises(PluginStateNotFound):
            plugin_state_storage.get_by_id("wrong", org.id)

        with self.assertRaises(PluginStateNotFound):
            plugin_state_storage.get_by_id(plugin.id, "wrong")

    def test_bare_boefje_storage(self):
        boefje = Boefje(id="test_boefje", name="Test", static=False)

        with self.plugin_storage as storage:
            storage.create_boefje(boefje)

        returned_boefje = storage.boefje_by_id(boefje.id)
        self.assertEqual(boefje, returned_boefje)

        storage.update_boefje(boefje.id, {"description": "4"})
        self.assertEqual(storage.boefje_by_id(boefje.id).description, "4")
        boefje.description = "4"

        all_plugins = storage.get_all()
        self.assertEqual(all_plugins, [boefje])

        with self.plugin_storage as storage:
            storage.delete_boefje_by_id(boefje.id)

        with self.assertRaises(PluginNotFound):
            storage.boefje_by_id(boefje.id)

    def test_rich_boefje_storage(self):
        boefje = Boefje(
            id="test_boefje",
            name="Test",
            version="v1.09",
            created=datetime.datetime(2010, 10, 10, 10, 10, 10, tzinfo=datetime.UTC),
            description="My Boefje",
            environment_keys=["api_key", "TOKEN"],
            scan_level=4,
            consumes=["Internet"],
            produces=[
                "image/png",
                "application/zip+json",
                "application/har+json",
                "application/json",
                "application/localstorage+json",
            ],
            oci_image="ghcr.io/test/image:123",
            oci_arguments=["host", "-n", "123123123123123123123"],
            static=False,
        )

        with self.plugin_storage as storage:
            storage.create_boefje(boefje)

        returned_boefje = storage.boefje_by_id(boefje.id)
        self.assertEqual(boefje, returned_boefje)

    def test_bare_normalizer_storage(self):
        normalizer = Normalizer(id="test_boefje", name="Test", static=False)

        with self.plugin_storage as storage:
            storage.create_normalizer(normalizer)

        returned_normalizer = storage.normalizer_by_id(normalizer.id)
        self.assertEqual(normalizer, returned_normalizer)

        storage.update_normalizer(normalizer.id, {"version": "v4"})
        self.assertEqual(storage.normalizer_by_id(normalizer.id).version, "v4")
        normalizer.version = "v4"

        all_plugins = storage.get_all()
        self.assertEqual(all_plugins, [normalizer])

        with self.plugin_storage as storage:
            storage.delete_normalizer_by_id(normalizer.id)

        with self.assertRaises(PluginNotFound):
            storage.normalizer_by_id(normalizer.id)

    def test_rich_normalizer_storage(self):
        normalizer = Normalizer(
            id="test_normalizer",
            name="Test",
            version="v1.19",
            created=datetime.datetime(2010, 10, 10, 10, 10, 10, tzinfo=datetime.UTC),
            description="My Normalizer",
            environment_keys=["api_key", "TOKEN"],
            scan_level=4,
            consumes=["Internet"],
            produces=[
                "image/png",
                "application/zip+json",
                "application/har+json",
                "application/json",
                "application/localstorage+json",
            ],
            static=False,
        )

        with self.plugin_storage as storage:
            storage.create_normalizer(normalizer)

        returned_normalizer = storage.normalizer_by_id(normalizer.id)
        self.assertEqual(normalizer, returned_normalizer)

    def test_plugin_storage(self):
        boefje = Boefje(id="test_boefje", name="Test", static=False)
        normalizer = Normalizer(id="test_boefje", name="Test", static=False)

        with self.plugin_storage as storage:
            storage.create_boefje(boefje)
            storage.create_normalizer(normalizer)

        self.assertEqual(storage.get_all(), [boefje, normalizer])
