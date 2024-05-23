from unittest import TestCase

from fastapi.testclient import TestClient

from boefjes.katalogus.api.organisations import check_organisation_exists
from boefjes.katalogus.api.root import app
from boefjes.katalogus.dependencies.plugins import get_plugin_service
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
                "kat_test",
                "kat_test_2",
                "kat_test_4",
                "kat_test_normalize",
                "kat_test_normalize_2",
            },
            {x["id"] for x in res.json()},
        )

    def test_list_filter_by_type(self):
        res = self.client.get("/v1/organisations/test-org/plugins?plugin_type=boefje")
        self.assertEqual(200, res.status_code)
        self.assertSetEqual(
            {
                "kat_test",
                "kat_test_2",
                "kat_test_4",
            },
            {x["id"] for x in res.json()},
        )

    def test_list_filter_by_state(self):
        res = self.client.get("/v1/organisations/test-org/plugins?state=true")
        self.assertEqual(200, res.status_code)
        plugins = res.json()
        self.assertSetEqual(
            {
                "kat_test_normalize",
                "kat_test_normalize_2",
            },
            {x["id"] for x in plugins},
        )
        self.assertTrue(all([x["enabled"] for x in plugins]))

    def test_list_filter_by_id(self):
        res = self.client.get("/v1/organisations/test-org/plugins?q=norm")
        self.assertEqual(200, res.status_code)
        self.assertSetEqual(
            {
                "kat_test_normalize",
                "kat_test_normalize_2",
            },
            {x["id"] for x in (res.json())},
        )

    def test_list_pagination(self):
        res = self.client.get("/v1/organisations/test-org/plugins?offset=2&limit=2")
        self.assertEqual(200, res.status_code)
        self.assertSetEqual(
            {
                "kat_test_4",
                "kat_test_normalize",
            },
            {x["id"] for x in (res.json())},
        )

    def test_list_plugins(self):
        res = self.client.get("/v1/organisations/test-org/plugins")
        self.assertEqual(200, res.status_code)
        self.assertListEqual(
            ["kat_test", "kat_test_2", "kat_test_4", "kat_test_normalize", "kat_test_normalize_2"],
            [x["id"] for x in res.json()],
        )

    def test_get_plugin(self):
        res = self.client.get("/v1/organisations/test-org/plugins/kat_test")
        self.assertEqual(200, res.status_code)
        assert "produces" in res.json()
        assert res.json()["produces"] == ["boefje/kat_test"]

    def test_non_existing_plugin(self):
        res = self.client.get("/v1/organisations/test-org/plugins/future-plugin")
        self.assertEqual(404, res.status_code)

    def test_default_enabled_property_list(self):
        res = self.client.get("/v1/organisations/test-org/plugins?plugin_type=boefje")
        self.assertEqual(200, res.status_code)
        self.assertFalse(any([plugin["enabled"] for plugin in res.json()]))

    def test_patching_enabled_state(self):
        res = self.client.patch(
            "/v1/organisations/test-org/plugins/test-boefje-1",
            json={"enabled": False},
        )
        self.assertEqual(200, res.status_code)

        res = self.client.get("/v1/organisations/test-org/plugins")
        self.assertEqual(200, res.status_code)
        self.assertEqual(
            {
                "kat_test": False,
                "kat_test_4": False,
                "kat_test_2": False,
                "kat_test_normalize": True,
                "kat_test_normalize_2": True,
            },
            {plugin["id"]: plugin["enabled"] for plugin in res.json()},
        )

    def test_patching_enabled_state_non_existing_org(self):
        res = self.client.patch(
            "/v1/organisations/non-existing-org/plugins/test-boefje-1",
            json={"enabled": False},
        )

        self.assertEqual(200, res.status_code)

        res = self.client.get("/v1/organisations/non-existing-org/plugins")
        self.assertEqual(200, res.status_code)
        self.assertEqual(
            {
                "kat_test": False,
                "kat_test_2": False,
                "kat_test_4": False,
                "kat_test_normalize": True,
                "kat_test_normalize_2": True,
            },
            {plugin["id"]: plugin["enabled"] for plugin in res.json()},
        )
