from unittest import TestCase

from fastapi.testclient import TestClient

from boefjes.katalogus.api import app
from boefjes.katalogus.dependencies.plugins import get_plugin_service
from boefjes.katalogus.routers.organisations import check_organisation_exists
from boefjes.katalogus.tests.test_plugin_service import mock_plugin_service


class TestPlugins(TestCase):
    def setUp(self) -> None:
        app.dependency_overrides[get_plugin_service] = mock_plugin_service
        app.dependency_overrides[check_organisation_exists] = lambda: None

        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides = {}

    def test_list(self):
        res = self.client.get("/v1/organisations/test-org/plugins")
        self.assertEqual(200, res.status_code)
        self.assertSetEqual(
            {
                "test-boefje-1",
                "test-boefje-2",
                "test-bit-1",
                "test-normalizer-1",
                "kat_test",
                "kat_test_2",
                "kat_test_normalize",
                "kat_test_normalize_2",
            },
            set([x["id"] for x in res.json()]),
        )

    def test_list_filter_by_type(self):
        res = self.client.get("/v1/organisations/test-org/plugins?plugin_type=boefje")
        self.assertEqual(200, res.status_code)
        self.assertSetEqual(
            {
                "test-boefje-1",
                "test-boefje-2",
                "kat_test",
                "kat_test_2",
            },
            set([x["id"] for x in res.json()]),
        )

    def test_list_filter_by_state(self):
        res = self.client.get("/v1/organisations/test-org/plugins?state=true")
        self.assertEqual(200, res.status_code)
        plugins = res.json()
        self.assertSetEqual(
            {
                "test-bit-1",
                "test-normalizer-1",
                "kat_test_normalize",
                "kat_test_normalize_2",
            },
            set([x["id"] for x in plugins]),
        )
        self.assertTrue(all([x["enabled"] for x in plugins]))

    def test_list_filter_by_id(self):
        res = self.client.get("/v1/organisations/test-org/plugins?q=kat")
        self.assertEqual(200, res.status_code)
        self.assertSetEqual(
            {
                "kat_test",
                "kat_test_2",
                "kat_test_normalize",
                "kat_test_normalize_2",
            },
            set([x["id"] for x in (res.json())]),
        )

    def test_list_pagination(self):
        res = self.client.get("/v1/organisations/test-org/plugins?offset=2&limit=2")
        self.assertEqual(200, res.status_code)
        self.assertSetEqual(
            {
                "test-bit-1",
                "test-normalizer-1",
            },
            set([x["id"] for x in (res.json())]),
        )

    def test_list_repository(self):
        res = self.client.get("/v1/organisations/test-org/repositories/test-repo/plugins")
        self.assertEqual(200, res.status_code)
        self.assertListEqual(
            ["test-boefje-1", "test-boefje-2"],
            list(res.json().keys()),
        )

    def test_list_repository2(self):
        res = self.client.get("/v1/organisations/test-org/repositories/test-repo-2/plugins")
        self.assertEqual(200, res.status_code)
        self.assertListEqual(
            ["test-bit-1", "test-normalizer-1"],
            list(res.json().keys()),
        )

    def test_get_plugin(self):
        res = self.client.get("/v1/organisations/test-org/repositories/test-repo/plugins/test-boefje-1")
        self.assertEqual(200, res.status_code)

        # Simpler endpoint works as well, but due to the mock the default mime_types are not dynamically added
        res = self.client.get("/v1/organisations/test-org/plugins/test-boefje-1")
        self.assertEqual(200, res.status_code)
        assert "mime_types" in res.json()
        assert not res.json()["mime_types"]

        # For boefjes that are pulled from the local repository, we actually get the default mime_types
        assert set(self.client.get("/v1/organisations/test-org/plugins/kat_test").json()["mime_types"]) == set(
            [
                "kat_test",
                "boefje/kat_test",
            ]
        )

    def test_non_existing_plugin(self):
        res = self.client.get("/v1/organisations/test-org/repositories/test-repo/plugins/future-plugin")
        self.assertEqual(404, res.status_code)

    def test_default_enabled_property_list(self):
        res = self.client.get("/v1/organisations/test-org/repositories/test-repo/plugins")
        self.assertEqual(200, res.status_code)
        self.assertFalse(any([plugin["enabled"] for plugin in res.json().values()]))

    def test_patching_enabled_state(self):
        res = self.client.patch(
            "/v1/organisations/test-org/repositories/test-repo/plugins/test-boefje-1",
            json={"enabled": False},
        )
        self.assertEqual(200, res.status_code)

        res = self.client.get("/v1/organisations/test-org/plugins")
        self.assertEqual(200, res.status_code)
        self.assertEqual(
            {
                "test-boefje-1": False,
                "test-boefje-2": False,
                "test-bit-1": True,
                "test-normalizer-1": True,
                "kat_test": False,
                "kat_test_2": False,
                "kat_test_normalize": True,
                "kat_test_normalize_2": True,
            },
            {plugin["id"]: plugin["enabled"] for plugin in res.json()},
        )

    def test_patching_enabled_state_non_existing_org(self):
        res = self.client.patch(
            "/v1/organisations/non-existing-org/repositories/test-repo/plugins/test-boefje-1",
            json={"enabled": False},
        )

        self.assertEqual(200, res.status_code)

        res = self.client.get("/v1/organisations/non-existing-org/plugins")
        self.assertEqual(200, res.status_code)
        self.assertEqual(
            {
                "test-boefje-1": False,
                "test-boefje-2": False,
                "test-bit-1": True,
                "test-normalizer-1": True,
                "kat_test": False,
                "kat_test_2": False,
                "kat_test_normalize": True,
                "kat_test_normalize_2": True,
            },
            {plugin["id"]: plugin["enabled"] for plugin in res.json()},
        )
