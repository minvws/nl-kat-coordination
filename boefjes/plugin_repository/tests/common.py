import io
from pathlib import Path

import fastapi
import yaml
from fastapi.testclient import TestClient

from boefjes.plugin_repository.models import Plugin
from boefjes.plugin_repository.utils.utils import parse_config

BASE_DIR = Path(__file__).parent
FIXTURES_DIR = BASE_DIR / "fixtures"
PLUGINS_DIR = BASE_DIR.joinpath("images")


def load_plugin(filename: str) -> Plugin:
    return parse_config(yaml.full_load(FIXTURES_DIR.joinpath(filename).read_bytes()))


def upload_plugin(
    client: TestClient, plugin: Plugin, metadata: bytes, rootfs: bytes
) -> fastapi.Response:
    plugin_file = yaml.dump(plugin.dict())

    res = client.post(
        "/plugins",
        files={
            "plugin_file": (
                "plugin_file",
                io.BytesIO(plugin_file.encode()),
                "text/yaml",
            ),
            "metadata": (
                "lxd.tar.xz",
                io.BytesIO(metadata),
                "application/x-tar",
            ),
            "rootfs": (
                "rootfs.squashfs",
                io.BytesIO(rootfs),
                "application/x-tar",
            ),
        },
    )

    return res
