import logging
from os.path import getsize
from pathlib import Path
from typing import Dict, List

import diskcache

from plugin_repository.config import PLUGINS_DIR
from plugin_repository.utils.hash import Hasher
from plugin_repository.models import Index, Image, File, CombinedFile
from plugin_repository.utils.utils import load_config_file

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_INDEX: Dict[Path, Index] = {}


def get_or_create_index(location: Path, reindex=False) -> Index:
    if not reindex and location in _INDEX:
        return _INDEX[location]

    index = create_index(location)
    _INDEX[location] = index

    return index


def create_index(location: Path) -> Index:
    index = Index()

    logger.info("Creating index...")
    for path in location.glob("**/*.yml"):
        config = load_config_file(path)

        image = Image(plugin=config, location=path.parent)
        files = get_files(path.parent)
        image.files.extend(files)
        index.images[str(image)] = image

        logger.info('Added image "%s"', image)

    logger.info("Created index with %d item(s)", len(index.images))

    return index


# todo: possible optimization to reduce looping again in generate_hashes?
def get_files(location: Path) -> List[File]:
    files: List[File] = []

    for path in location.iterdir():
        file = File(location=path, size=getsize(path))
        if file.ftype == "lxd.tar.xz":
            file = CombinedFile(**file.dict())
        files.append(file)

    cache = diskcache.Cache(PLUGINS_DIR)
    hasher = Hasher(cache)
    hasher.generate_hashes(files)

    return files
