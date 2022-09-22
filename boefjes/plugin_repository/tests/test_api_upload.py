import shutil
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from fastapi.testclient import TestClient

from boefjes.plugin_repository.api.repository import create_app
from boefjes.plugin_repository.tests.common import load_plugin, upload_plugin

TEMP_PLUGINS_DIR = Path(tempfile.mkdtemp())


@patch("boefjes.plugin_repository.utils.index.PLUGINS_DIR", TEMP_PLUGINS_DIR)
class TestUploadAPI(TestCase):
    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(TEMP_PLUGINS_DIR)

    def setUp(self) -> None:
        self.client = TestClient(create_app(TEMP_PLUGINS_DIR))

    @patch(
        "boefjes.plugin_repository.api.routers.plugins.PLUGINS_DIR", TEMP_PLUGINS_DIR
    )
    def test_upload_boefje_plugin(self):
        plugin = load_plugin("test-boefje.yml")

        res = upload_plugin(self.client, plugin, b"metadata", b"rootfs")
        self.assertEqual(202, res.status_code)

        res = self.client.get("/plugins")
        self.assertDictEqual(plugin.dict(), res.json()[str(plugin)])

    @patch(
        "boefjes.plugin_repository.api.routers.plugins.PLUGINS_DIR", TEMP_PLUGINS_DIR
    )
    def test_upload_normalizer_plugin(self):
        plugin = load_plugin("test-normalizer.yml")

        res = upload_plugin(self.client, plugin, b"metadata", b"rootfs")
        self.assertEqual(202, res.status_code)

        res = self.client.get("/plugins")
        self.assertDictEqual(plugin.dict(), res.json()[str(plugin)])

    @patch(
        "boefjes.plugin_repository.api.routers.plugins.PLUGINS_DIR", TEMP_PLUGINS_DIR
    )
    def test_upload_bit_plugin(self):
        plugin = load_plugin("test-bit.yml")

        res = upload_plugin(self.client, plugin, b"metadata", b"rootfs")
        self.assertEqual(202, res.status_code)

        res = self.client.get("/plugins", params={"plugin_type": "bit"})
        self.assertDictEqual(plugin.dict(), res.json()[str(plugin)])
