import time
import unittest
from unittest import mock

from scheduler import config, models, storage
from scheduler.connectors import services
from scheduler.utils import remove_trailing_slash

from tests.factories import PluginFactory


class BytesTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.config = config.settings.Settings()
        self.service_bytes = services.Bytes(
            host=remove_trailing_slash(str(self.config.host_bytes)),
            user=self.config.host_bytes_user,
            password=self.config.host_bytes_password,
            source="scheduler_test",
        )

    def test_login(self):
        self.service_bytes.login()

        self.assertIsNotNone(self.service_bytes.headers)
        self.assertIsNotNone(self.service_bytes.headers.get("Authorization"))

    @unittest.skip
    def test_expired_token_refresh(self):
        self.service_bytes.get_last_run_boefje(
            boefje_id="boefje-1",
            input_ooi="ooi-1",
            organization_id="org-1",
        )
        initial_token = id(self.service_bytes.headers.get("Authorization"))

        time.sleep(70)

        self.service_bytes.get_last_run_boefje(
            boefje_id="boefje-1",
            input_ooi="ooi-1",
            organization_id="org-1",
        )
        refresh_token = id(self.service_bytes.headers.get("Authorization"))

        self.assertNotEqual(initial_token, refresh_token)


class KatalogusTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.config = config.settings.Settings()
        self.dbconn = storage.DBConn(str(self.config.db_uri))

        self.service_katalogus = services.Katalogus(
            host=remove_trailing_slash(str(self.config.host_katalogus)),
            source="scheduler_test",
            cache_ttl=12345,
        )

    def tearDown(self) -> None:
        self.service_katalogus.organisations_plugin_cache.reset()
        self.service_katalogus.organisations_boefje_type_cache.reset()
        self.service_katalogus.organisations_normalizer_type_cache.reset()

    @mock.patch("scheduler.connectors.services.Katalogus.get_organisations")
    def test_flush_organisations_plugin_cache(self, mock_get_organisations):
        # Mock
        mock_get_organisations.return_value = [
            models.Organisation(id="org-1", name="org-1"),
            models.Organisation(id="org-2", name="org-2"),
        ]

        # Act
        self.service_katalogus.flush_organisations_plugin_cache()

        # Assert
        self.assertCountEqual(self.service_katalogus.organisations_plugin_cache.cache.keys(), ("org-1", "org-2"))

    @mock.patch("scheduler.connectors.services.Katalogus.get_organisations")
    def test_flush_organisations_plugin_cache_empty(self, mock_get_organisations):
        # Mock
        mock_get_organisations.return_value = []

        # Act
        self.service_katalogus.flush_organisations_plugin_cache()

        # Assert
        self.assertDictEqual(self.service_katalogus.organisations_plugin_cache.cache, {})

    @mock.patch("scheduler.connectors.services.Katalogus.get_plugins_by_organisation")
    @mock.patch("scheduler.connectors.services.Katalogus.get_organisations")
    def test_flush_organisations_boefje_type_cache(self, mock_get_organisations, mock_get_plugins_by_organisation):
        # Mock
        mock_get_organisations.return_value = [
            models.Organisation(id="org-1", name="org-1"),
            models.Organisation(id="org-2", name="org-2"),
        ]

        mock_get_plugins_by_organisation.return_value = [
            PluginFactory(id="plugin-1", type="boefje", enabled=True, consumes=["Hostname"]),
            PluginFactory(id="plugin-2", type="boefje", enabled=True, consumes=["Hostname"]),
            PluginFactory(id="plugin-3", type="boefje", enabled=False, consumes=["Hostname"]),
            PluginFactory(id="plugin-4", type="normalizer", enabled=True, consumes=["Hostname"]),
        ]

        # Act
        self.service_katalogus.flush_organisations_boefje_type_cache()

        # Assert
        self.assertEqual(len(self.service_katalogus.organisations_boefje_type_cache), 2)
        self.assertIsNotNone(self.service_katalogus.organisations_boefje_type_cache.get("org-1"))
        self.assertIsNotNone(self.service_katalogus.organisations_boefje_type_cache.get("org-1").get("Hostname"))
        self.assertEqual(len(self.service_katalogus.organisations_boefje_type_cache.get("org-1").get("Hostname")), 2)
        self.assertIsNotNone(self.service_katalogus.organisations_boefje_type_cache.get("org-2"))
        self.assertIsNotNone(self.service_katalogus.organisations_boefje_type_cache.get("org-2").get("Hostname"))
        self.assertEqual(len(self.service_katalogus.organisations_boefje_type_cache.get("org-2").get("Hostname")), 2)

    @mock.patch("scheduler.connectors.services.Katalogus.get_plugins_by_organisation")
    @mock.patch("scheduler.connectors.services.Katalogus.get_organisations")
    def test_flush_organisations_normalizer_type_cache(self, mock_get_organisations, mock_get_plugins_by_organisation):
        # Mock
        mock_get_organisations.return_value = [
            models.Organisation(id="org-1", name="org-1"),
            models.Organisation(id="org-2", name="org-2"),
        ]

        mock_get_plugins_by_organisation.return_value = [
            PluginFactory(id="plugin-1", type="normalizer", enabled=True, consumes=["Hostname"]),
            PluginFactory(id="plugin-2", type="normalizer", enabled=True, consumes=["Hostname"]),
            PluginFactory(id="plugin-3", type="normalizer", enabled=False, consumes=["Hostname"]),
            PluginFactory(id="plugin-4", type="boefje", enabled=True, consumes=["Hostname"]),
        ]

        # Act
        self.service_katalogus.flush_organisations_normalizer_type_cache()

        # Assert
        self.assertEqual(len(self.service_katalogus.organisations_normalizer_type_cache), 2)
        self.assertIsNotNone(self.service_katalogus.organisations_normalizer_type_cache.get("org-1"))
        self.assertIsNotNone(self.service_katalogus.organisations_normalizer_type_cache.get("org-1").get("Hostname"))
        self.assertEqual(
            len(self.service_katalogus.organisations_normalizer_type_cache.get("org-1").get("Hostname")), 2
        )
        self.assertIsNotNone(self.service_katalogus.organisations_normalizer_type_cache.get("org-2"))
        self.assertIsNotNone(self.service_katalogus.organisations_normalizer_type_cache.get("org-2").get("Hostname"))
        self.assertEqual(
            len(self.service_katalogus.organisations_normalizer_type_cache.get("org-2").get("Hostname")), 2
        )

    @mock.patch("scheduler.connectors.services.Katalogus.get_plugins_by_organisation")
    def test_get_new_boefjes_by_org_id(self, mock_get_plugins_by_organisation):
        # Mock
        mock_get_plugins_by_organisation.side_effect = [
            [
                PluginFactory(id="plugin-1", type="boefje", enabled=True, consumes=["Hostname"]),
                PluginFactory(id="plugin-2", type="boefje", enabled=True, consumes=["Hostname"]),
                PluginFactory(id="plugin-3", type="boefje", enabled=False, consumes=["Hostname"]),
                PluginFactory(id="plugin-4", type="normalizer", enabled=True, consumes=["Hostname"]),
            ],
            [
                PluginFactory(id="plugin-1", type="boefje", enabled=True, consumes=["Hostname"]),
                PluginFactory(id="plugin-3", type="boefje", enabled=False, consumes=["Hostname"]),
                PluginFactory(id="plugin-4", type="normalizer", enabled=True, consumes=["Hostname"]),
                PluginFactory(id="plugin-5", type="boefje", enabled=True, consumes=["Hostname"]),
            ],
        ]

        # Act
        new_boefjes = self.service_katalogus.get_new_boefjes_by_org_id("org-1")

        # Assert
        self.assertEqual(len(self.service_katalogus.organisations_new_boefjes_cache), 2)
        self.assertIsNotNone(self.service_katalogus.organisations_new_boefjes_cache.get("org-1"))
        self.assertEqual(len(self.service_katalogus.organisations_new_boefjes_cache.get("org-1")), 2)
        self.assertIsNotNone(self.service_katalogus.organisations_new_boefjes_cache.get("org-1").get("plugin-1"))
        self.assertIsNotNone(self.service_katalogus.organisations_new_boefjes_cache.get("org-1").get("plugin-2"))
        self.assertEqual(len(new_boefjes), 2)
        self.assertEqual(new_boefjes[0].id, "plugin-1")
        self.assertEqual(new_boefjes[1].id, "plugin-2")

        # Act
        new_boefjes = self.service_katalogus.get_new_boefjes_by_org_id("org-1")

        # Assert
        self.assertEqual(len(self.service_katalogus.organisations_new_boefjes_cache), 2)
        self.assertIsNotNone(self.service_katalogus.organisations_new_boefjes_cache.get("org-1"))
        self.assertEqual(len(self.service_katalogus.organisations_new_boefjes_cache.get("org-1")), 2)
        self.assertIsNotNone(self.service_katalogus.organisations_new_boefjes_cache.get("org-1").get("plugin-5"))
        self.assertIsNotNone(self.service_katalogus.organisations_new_boefjes_cache.get("org-1").get("plugin-5"))
        self.assertEqual(len(new_boefjes), 1)
        self.assertEqual(new_boefjes[0].id, "plugin-5")
