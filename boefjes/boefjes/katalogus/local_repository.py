import json
import logging
import pkgutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from boefjes.katalogus.models import PluginType
from boefjes.plugins.models import (
    BOEFJE_DEFINITION_FILE,
    BOEFJES_DIR,
    ENTRYPOINT_BOEFJES,
    ENTRYPOINT_NORMALIZERS,
    NORMALIZER_DEFINITION_FILE,
    BoefjeResource,
    ModuleException,
    NormalizerResource,
)

logger = logging.getLogger(__name__)


class LocalPluginRepository:
    def __init__(self, path: Path):
        self.path = path
        self._cached_boefjes: Optional[Dict[str, Any]] = None
        self._cached_normalizers: Optional[Dict[str, Any]] = None

    def get_all(self) -> List[PluginType]:
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

        raise Exception(f"Can't find plugin {plugin_id}")

    def schema(self, id_: str) -> Optional[Dict]:
        boefjes = self.resolve_boefjes()

        if id_ not in boefjes:
            return None

        path = boefjes[id_].path / "schema.json"

        if not path.exists():
            logger.debug("Did not find schema for boefje %s", boefjes[id_])
            return None

        return json.loads(path.read_text())

    def cover_path(self, id_: str) -> Path:
        boefjes = self.resolve_boefjes()

        if id_ not in boefjes:
            return self.default_cover_path()

        boefje = boefjes[id_]
        path = boefje.path / "cover.jpg"

        if not path.exists():
            logger.debug("Did not find cover for boefje %s", boefje)
            return self.default_cover_path()

        logger.debug("Found cover for boefje %s", boefje)

        return path

    def default_cover_path(self) -> Path:
        return self.path / "default_cover.jpg"

    def description_path(self, id_: str) -> Optional[Path]:
        boefjes = self.resolve_boefjes()

        if id_ not in boefjes:
            return None

        return boefjes[id_].path / "description.md"

    def resolve_boefjes(self) -> Dict[str, BoefjeResource]:
        if self._cached_boefjes:
            return self._cached_boefjes

        paths_and_packages = self._find_packages_in_path_containing_files([BOEFJE_DEFINITION_FILE, ENTRYPOINT_BOEFJES])
        boefje_resources = []

        for path, package in paths_and_packages:
            try:
                boefje_resources.append(BoefjeResource(path, package))
            except ModuleException as exc:
                logger.exception(exc)

        self._cached_boefjes = {resource.boefje.id: resource for resource in boefje_resources}

        return self._cached_boefjes

    def resolve_normalizers(self) -> Dict[str, NormalizerResource]:
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

    def _find_packages_in_path_containing_files(self, files: List[str]) -> List[Tuple[Path, str]]:
        prefix = self.create_relative_import_statement_from_cwd(self.path)
        paths = []

        for package in pkgutil.walk_packages([str(self.path)], prefix):
            if not package.ispkg:
                logging.debug("%s is not a package", package.name)
                continue

            path = self.path / package.name.replace(prefix, "").replace(".", "/")
            not_present_files = [file for file in files if not (path / file).exists()]

            if not_present_files:
                logging.debug("Files %s not found for %s", not_present_files, package.name)
                continue

            paths.append((path, package.name))

        return paths

    @staticmethod
    def create_relative_import_statement_from_cwd(package_dir: Path) -> str:
        relative_path = str(package_dir.absolute()).replace(str(Path.cwd()), "")  # e.g. "/boefjes/plugins"

        return f"{relative_path[1:].replace('/', '.')}."  # Turns into "boefjes.plugins."


def get_local_repository():
    return LocalPluginRepository(BOEFJES_DIR)
