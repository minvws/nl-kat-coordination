import json
import pkgutil
from pathlib import Path
from typing import Any

import structlog

from boefjes.models import PluginType
from boefjes.plugins.models import (
    BOEFJE_DEFINITION_FILE,
    BOEFJES_DIR,
    ENTRYPOINT_NORMALIZERS,
    NORMALIZER_DEFINITION_FILE,
    BoefjeResource,
    ModuleException,
    NormalizerResource,
)

logger = structlog.get_logger(__name__)


class LocalPluginRepository:
    def __init__(self, path: Path):
        self.path = path
        self._cached_boefjes: dict[str, Any] | None = None
        self._cached_normalizers: dict[str, Any] | None = None

    def get_all(self) -> list[PluginType]:
        all_plugins = [boefje_resource.boefje for boefje_resource in self.resolve_boefjes().values()]
        normalizers = [normalizer_resource.normalizer for normalizer_resource in self.resolve_normalizers().values()]

        all_plugins += normalizers

        return all_plugins

    def by_id(self, plugin_id: str) -> PluginType:
        boefjes = self.resolve_boefjes()

        if plugin_id in boefjes:
            return boefjes[plugin_id].boefje

        normalizers = self.resolve_normalizers()

        if plugin_id in normalizers:
            return normalizers[plugin_id].normalizer

        raise KeyError(f"Can't find plugin {plugin_id}")

    def schema(self, id_: str) -> dict | None:
        boefjes = self.resolve_boefjes()

        if id_ not in boefjes:
            return None

        path = boefjes[id_].path / "schema.json"

        if not path.exists():
            logger.debug("Did not find schema for boefje %s", boefjes[id_])
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
        if self._cached_boefjes:
            return self._cached_boefjes

        paths_and_packages = self._find_packages_in_path_containing_files([BOEFJE_DEFINITION_FILE])
        boefje_resources = []

        for path, package in paths_and_packages:
            try:
                boefje_resources.append(BoefjeResource(path, package))
            except ModuleException as exc:
                logger.exception(exc)

        self._cached_boefjes = {resource.boefje.id: resource for resource in boefje_resources}

        return self._cached_boefjes

    def resolve_normalizers(self) -> dict[str, NormalizerResource]:
        if self._cached_normalizers:
            return self._cached_normalizers

        paths_and_packages = self._find_packages_in_path_containing_files(
            [NORMALIZER_DEFINITION_FILE, ENTRYPOINT_NORMALIZERS]
        )
        normalizer_resources = []

        for path, package in paths_and_packages:
            try:
                normalizer_resources.append(NormalizerResource(path, package))
            except ModuleException as exc:
                logger.exception(exc)

        self._cached_normalizers = {resource.normalizer.id: resource for resource in normalizer_resources}

        return self._cached_normalizers

    def _find_packages_in_path_containing_files(self, required_files: list[str]) -> list[tuple[Path, str]]:
        prefix = self.create_relative_import_statement_from_cwd(self.path)
        paths = []

        for package in pkgutil.walk_packages([str(self.path)], prefix):
            if not package.ispkg:
                logger.debug("%s is not a package", package.name)
                continue

            path = self.path / package.name.replace(prefix, "").replace(".", "/")
            missing_files = [file for file in required_files if not (path / file).exists()]

            if missing_files:
                logger.debug("Files %s not found for %s", missing_files, package.name)
                continue

            paths.append((path, package.name))

        return paths

    @staticmethod
    def create_relative_import_statement_from_cwd(package_dir: Path) -> str:
        relative_path = str(package_dir.absolute()).replace(str(Path.cwd()), "")  # e.g. "/boefjes/plugins"

        return f"{relative_path[1:].replace('/', '.')}."  # Turns into "boefjes.plugins."


def get_local_repository():
    return LocalPluginRepository(BOEFJES_DIR)
