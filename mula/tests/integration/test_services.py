import copy
import time
import unittest
import urllib.parse
from unittest import mock

from scheduler import config, models, storage
from scheduler.connectors import services
from scheduler.utils import remove_trailing_slash

from tests.factories import OrganisationFactory, PluginFactory


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

    def test_login_token_refresh(self):
        self.service_bytes.login()
        initial_token = copy.deepcopy(self.service_bytes.headers.get("Authorization"))

        self.service_bytes.login()
        refresh_token = copy.deepcopy(self.service_bytes.headers.get("Authorization"))

        self.assertNotEqual(initial_token, refresh_token)

    def test_expired_token_refresh(self):
        self.service_bytes.get_last_run_boefje(
            boefje_id="boefje-1",
            input_ooi="ooi-1",
            organization_id="org-1",
        )
        initial_token = copy.deepcopy(self.service_bytes.headers.get("Authorization"))

        time.sleep(70)

        self.service_bytes.get_last_run_boefje(
            boefje_id="boefje-1",
            input_ooi="ooi-1",
            organization_id="org-1",
        )
        refresh_token = copy.deepcopy(self.service_bytes.headers.get("Authorization"))

        self.assertNotEqual(initial_token, refresh_token)

    # TODO: do we want to mock the response here?
    def test_get_last_run_boefje(self):
        pass

    # TODO: do we want to mock the response here?
    def test_get_last_run_boefje_by_organisation_id(self):
        pass


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
        models.Base.metadata.drop_all(self.dbconn.engine)

    def test_get_organisations(self):
        orgs = self.service_katalogus.get_organisations()
        self.assertIsInstance(orgs, list)
        self.assertEqual(len(orgs), 0)

    @mock.patch("scheduler.connectors.services.Katalogus.get_organisations")
    def test_flush_organisations_plugin_cache(self, mock_get_organisations):
        # Mock
        mock_get_organisations.return_value = [
             OrganisationFactory(id="org-1"),
             OrganisationFactory(id="org-2"),
        ]

        # Act
        self.service_katalogus.flush_organisations_plugin_cache()

        # Assert
        self.assertEqual(len(self.service_katalogus.organisations_plugin_cache), 2)
        self.assertIsNotNone(self.service_katalogus.organisations_plugin_cache.get("org-1"))

    @mock.patch("scheduler.connectors.services.Katalogus.get_organisations")
    def test_flush_organisations_plugin_cache_empty(self, mock_get_organisations):
        # Mock
        mock_get_organisations.return_value = []

        # Act
        self.service_katalogus.flush_organisations_plugin_cache()

        # Assert
        self.assertEqual(len(self.service_katalogus.organisations_plugin_cache), 0)
        self.assertIsNone(self.service_katalogus.organisations_plugin_cache.get("org-1"))

    @mock.patch("scheduler.connectors.services.Katalogus.get_plugins_by_organisation")
    @mock.patch("scheduler.connectors.services.Katalogus.get_organisations")
    def test_flush_organisations_boefje_type_cache(self, mock_get_organisations, mock_get_plugins_by_organisation):
        # Mock
        mock_get_organisations.return_value = [
            OrganisationFactory(id="org-1"),
            OrganisationFactory(id="org-2"),
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
            OrganisationFactory(id="org-1"),
            OrganisationFactory(id="org-2"),
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
        self.assertEqual(len(self.service_katalogus.organisations_normalizer_type_cache.get("org-1").get("Hostname")), 2)
        self.assertIsNotNone(self.service_katalogus.organisations_normalizer_type_cache.get("org-2"))
        self.assertIsNotNone(self.service_katalogus.organisations_normalizer_type_cache.get("org-2").get("Hostname"))
        self.assertEqual(len(self.service_katalogus.organisations_normalizer_type_cache.get("org-2").get("Hostname")), 2)

    def test_get_plugins_by_org_id(self):
        pass

    def test_get_plugins_by_org_id_expired(self):
        pass

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


class OctopoesTestCase(unittest.TestCase):
    def setUp(self):
        self.config = config.settings.Settings()
        self.service_octopoes = services.Octopoes(
            host=remove_trailing_slash(str(self.config.host_octopoes)),
            source="scheduler_test",
            orgs=[OrganisationFactory(id="org-1"), OrganisationFactory(id="org-2")],
            timeout=5,
        )

    def test_is_host_available(self):
        parsed_url = urllib.parse.urlparse(str(self.config.host_octopoes))
        hostname, port = parsed_url.hostname, parsed_url.port
        response = self.service_octopoes.is_host_available(hostname, port)
        self.assertTrue(response)

    def test_is_healthy(self):
        response = self.service_octopoes.is_healthy()
        self.assertTrue(response)
