import shutil
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from fastapi.testclient import TestClient

from boefjes.plugin_repository.api.repository import create_app
from boefjes.plugin_repository.tests.common import (
    PLUGINS_DIR,
    load_plugin,
    upload_plugin,
)


@patch("boefjes.plugin_repository.api.routers.simplestreams.PLUGINS_DIR", PLUGINS_DIR)
@patch("boefjes.plugin_repository.utils.index.PLUGINS_DIR", PLUGINS_DIR)
class TestAPI(TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app(PLUGINS_DIR))

    def test_index_file(self):
        res = self.client.get("/streams/v1/index.json")

        self.assertEqual(200, res.status_code)
        self.assertEqual("application/json", res.headers["Content-Type"])
        self.assertSetEqual(
            {
                "test-bit-1",
                "test-boefje-2",
                "test-boefje-1",
                "test-normalizer-1",
            },
            set(res.json()["index"]["images"]["products"]),
        )

    def test_images_file(self):
        res = self.client.get("/streams/v1/images.json")

        self.assertEqual(200, res.status_code)
        self.assertEqual("application/json", res.headers["Content-Type"])
        self.assertEqual(
            {
                "test-normalizer-1",
                "test-bit-1",
                "test-boefje-2",
                "test-boefje-1",
            },
            res.json()["products"].keys(),
        )

    def test_image_download(self):
        res = self.client.get("/streams/v1/images.json")

        data = res.json()["products"]["test-boefje-1"]["versions"]
        version = next(iter(data.keys()))
        data = data[version]["items"]["boefje.yml"]
        path = data["path"]
        size = data["size"]

        res = self.client.get(path)
        self.assertEqual(200, res.status_code)
        self.assertEqual(size, int(res.headers["Content-Length"]))

    def test_upload_and_list(self):
        directory = Path(tempfile.mkdtemp())

        # upload plugin
        plugin = load_plugin("test-boefje.yml")
        with patch(
            "boefjes.plugin_repository.api.routers.plugins.PLUGINS_DIR", directory
        ):
            res = upload_plugin(self.client, plugin, b"metadata", b"rootfs")
        self.assertEqual(202, res.status_code)

        # retrieve images index
        with patch(
            "boefjes.plugin_repository.api.routers.simplestreams.PLUGINS_DIR", directory
        ):
            res = self.client.get("/streams/v1/index.json")

        # make sure the plugin is there
        self.assertEqual(200, res.status_code)
        self.assertEqual("application/json", res.headers["Content-Type"])
        self.assertListEqual(
            [
                "kat-test-boefje",
            ],
            res.json()["index"]["images"]["products"],
        )

        shutil.rmtree(directory)
