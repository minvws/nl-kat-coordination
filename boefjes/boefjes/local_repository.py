import json
import pkgutil
from functools import cache, lru_cache
from pathlib import Path

import structlog

from boefjes.models import PluginType
from boefjes.plugins.models import (
    BOEFJE_DEFINITION_FILE,
    BOEFJES_DIR,
    ENTRYPOINT_NORMALIZERS,
    NORMALIZER_DEFINITION_FILE,
    SCHEMA_FILE,
    BoefjeResource,
    ModuleException,
    NormalizerResource,
    hash_path,
)

logger = structlog.get_logger(__name__)


class LocalPluginRepository:
    def __init__(self, path: Path):
        self.path = path

    def get_all(self) -> list[PluginType]:
        boefjes = [resource.boefje for resource in self.resolve_boefjes().values()]
        normalizers = [resource.normalizer for resource in self.resolve_normalizers().values()]
        return boefjes + normalizers

    def by_id(self, plugin_id: str) -> PluginType:
        boefjes = self.resolve_boefjes()

        if plugin_id in boefjes:
            return boefjes[plugin_id].boefje

        normalizers = self.resolve_normalizers()

        if plugin_id in normalizers:
            return normalizers[plugin_id].normalizer

        raise KeyError(f"Can't find plugin {plugin_id}")

    def by_name(self, plugin_name: str) -> PluginType:
        boefjes = {resource.boefje.name: resource for resource in self.resolve_boefjes().values()}

        if plugin_name in boefjes:
            return boefjes[plugin_name].boefje

        normalizers = {resource.normalizer.name: resource for resource in self.resolve_normalizers().values()}

        if plugin_name in normalizers:
            return normalizers[plugin_name].normalizer

        raise KeyError(f"Can't find plugin {plugin_name}")

    def schema(self, id_: str) -> dict | None:
        boefjes = self.resolve_boefjes()

        if id_ not in boefjes:
            return None

        path = boefjes[id_].path / SCHEMA_FILE

        if not path.exists():
            logger.debug("Did not find schema for boefje %s", id_)
            return None

        return json.loads(path.read_text())

    def cover_path(self, plugin_id: str) -> Path:
        boefjes = self.resolve_boefjes()
        normalizers = self.resolve_normalizers()
        default_cover_path = self.default_cover_path()
        plugin: BoefjeResource | NormalizerResource

        if plugin_id in boefjes:
            plugin = boefjes[plugin_id]
            cover_path = plugin.path / "cover.jpg"
        elif plugin_id in normalizers:
            plugin = normalizers[plugin_id]
            cover_path = plugin.path / "normalizer_cover.jpg"
        else:
            cover_path = default_cover_path

        if not cover_path.exists():
            logger.debug("Did not find cover for plugin %s", plugin_id)
            return default_cover_path

        return cover_path

    def default_cover_path(self) -> Path:
        return self.path / "default_cover.jpg"

    def description_path(self, id_: str) -> Path | None:
        boefjes = self.resolve_boefjes()

        if id_ not in boefjes:
            return None

        return boefjes[id_].path / "description.md"

    def resolve_boefjes(self) -> dict[str, BoefjeResource]:
        return _cached_resolve_boefjes(self.path)

    def resolve_normalizers(self) -> dict[str, NormalizerResource]:
        return _cached_resolve_normalizers(self.path)


@cache
def _cached_resolve_boefjes(path: Path) -> dict[str, BoefjeResource]:
    paths_and_packages = _find_packages_in_path_containing_files(path, (BOEFJE_DEFINITION_FILE,))
    boefje_resources = []

    for path, package in paths_and_packages:
        try:
            boefje_resources.append(get_boefje_resource(path, package, hash_path(path)))
        except ModuleException as exc:
            logger.exception(exc)

    return {resource.boefje.id: resource for resource in boefje_resources}


@cache
def _cached_resolve_normalizers(path: Path) -> dict[str, NormalizerResource]:
    paths_and_packages = _find_packages_in_path_containing_files(
        path, (NORMALIZER_DEFINITION_FILE, ENTRYPOINT_NORMALIZERS)
    )
    normalizer_resources = []

    for path, package in paths_and_packages:
        try:
            normalizer_resources.append(get_normalizer_resource(path, package, hash_path(path)))
        except ModuleException as exc:
            logger.exception(exc)

    return {resource.normalizer.id: resource for resource in normalizer_resources}


def _find_packages_in_path_containing_files(path: Path, required_files: tuple[str, ...]) -> list[tuple[Path, str]]:
    prefix = create_relative_import_statement_from_cwd(path)
    paths = []

    for package in pkgutil.walk_packages([str(path)], prefix):
        if not package.ispkg:
            logger.debug("%s is not a package", package.name)
            continue

        new_path = path / package.name.replace(prefix, "").replace(".", "/")
        missing_files = [file for file in required_files if not (new_path / file).exists()]

        if missing_files:
            logger.debug("Files %s not found for %s", missing_files, package.name)
            continue

        paths.append((new_path, package.name))

    return paths


def create_relative_import_statement_from_cwd(package_dir: Path) -> str:
    relative_path = str(package_dir.absolute()).replace(str(Path.cwd()), "")  # e.g. "/boefjes/plugins"

    return f"{relative_path[1:].replace('/', '.')}."  # Turns into "boefjes.plugins."


@lru_cache(maxsize=200)
def get_boefje_resource(path: Path, package: str, path_hash: str):
    """The cache size in theory only has to be the amount of local boefjes available, but 200 gives us some extra
    space. Adding the hash to the arguments makes sure we refresh this."""

    return BoefjeResource(path, package, path_hash)


@lru_cache(maxsize=200)
def get_normalizer_resource(path: Path, package: str, path_hash: str):
    """The cache size in theory only has to be the amount of local normalizers available, but 200 gives us some extra
    space. Adding the hash to the arguments makes sure we refresh this."""

    return NormalizerResource(path, package)


def get_local_repository():
    return LocalPluginRepository(BOEFJES_DIR)
