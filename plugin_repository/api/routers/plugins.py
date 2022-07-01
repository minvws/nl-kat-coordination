import logging
from pathlib import Path
from typing import Dict, Optional

import pydantic
import yaml
from fastapi import (
    APIRouter,
    HTTPException,
    BackgroundTasks,
    status,
    File,
    UploadFile,
    Depends,
)

from plugin_repository.config import PLUGINS_DIR
from plugin_repository.models import (
    Plugin,
    PluginType,
    Index,
    PluginChoice,
)
from plugin_repository.utils.index import get_or_create_index
from plugin_repository.utils.utils import parse_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/plugins")


def get_index() -> Index:
    return get_or_create_index(PLUGINS_DIR)


def _get_plugin(
    plugin: str,
    index: Index = Depends(get_index),
) -> Plugin:
    if plugin not in index.images:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown plugin")

    return index.images[plugin].plugin


@router.get("", response_model=Dict[str, PluginType])
def list_plugins(
    index: Index = Depends(get_index), plugin_choice: Optional[PluginChoice] = None
) -> Dict[str, Plugin]:
    ret = {
        name: image.plugin
        for name, image in index.images.items()
        if plugin_choice is None or image.plugin.type == plugin_choice.value
    }

    return ret


@router.get("/{plugin}", response_model=PluginType)
def get_plugin(plugin: Plugin = Depends(_get_plugin)) -> Plugin:
    return plugin


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def add_plugin(
    background_tasks: BackgroundTasks,
    plugin_file: UploadFile = File(...),
    metadata: UploadFile = File(...),
    rootfs: UploadFile = File(...),
):
    try:
        manifest = plugin_file.file.read()
        config = yaml.full_load(manifest)
        plugin = parse_config(config)
    except yaml.YAMLError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except pydantic.ValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors())

    background_tasks.add_task(
        _handle_plugin_upload, PLUGINS_DIR, manifest, plugin, metadata, rootfs
    )

    return {}


def _handle_plugin_upload(
    location: Path,
    manifest: bytes,
    plugin: PluginType,
    metadata: UploadFile,
    rootfs: UploadFile,
) -> None:
    # create plugin directory
    path = location.joinpath(str(plugin))
    path.mkdir(exist_ok=True)

    # copy files from user to plugin directory
    path.joinpath(plugin.type).with_suffix(".yml").write_bytes(manifest)
    path.joinpath(metadata.filename).write_bytes(metadata.file.read())
    path.joinpath(rootfs.filename).write_bytes(rootfs.file.read())

    # reindex
    get_or_create_index(location, True)
