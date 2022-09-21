from unittest import TestCase
from unittest.mock import patch

from fastapi.testclient import TestClient

from boefjes.plugin_repository.api.repository import create_app
from boefjes.plugin_repository.tests.common import PLUGINS_DIR


@patch("boefjes.plugin_repository.api.routers.plugins.PLUGINS_DIR", PLUGINS_DIR)
class TestAPI(TestCase):
    def setUp(self) -> None:
        self.app = create_app(PLUGINS_DIR)
        self.client = TestClient(self.app)

    def test_list_plugins(self):
        plugins = [
            ("boefje", {"test-boefje-1", "test-boefje-2"}),
            ("normalizer", {"test-normalizer-1"}),
            ("bit", {"test-bit-1"}),
        ]

        for plugin_choice, plugin_names in plugins:
            with self.subTest(plugin_choice=plugin_choice, plugins=plugin_names):
                res = self.client.get(
                    f"/plugins/", params={"plugin_choice": plugin_choice}
                )
                self.assertEqual(200, res.status_code)
                self.assertEqual(plugin_names, res.json().keys())

    def test_get_plugin(self):
        plugins = [
            ("boefjes", "test-boefje-1", "0.1"),
            ("normalizers", "test-normalizer-1", "0.1"),
            ("bits", "test-bit-1", "0.1"),
        ]

        for plugin_type, plugin, version in plugins:
            with self.subTest(plugin=plugin):
                res = self.client.get(f"/plugins/{plugin}")
                self.assertEqual(200, res.status_code)
                data = res.json()
                self.assertEqual(plugin, data["id"])
                self.assertEqual(version, data["version"])

    def test_non_existing_plugin(self):
        res = self.client.get("/plugins/boefjes/future-boefje:2.0")
        self.assertEqual(404, res.status_code)
