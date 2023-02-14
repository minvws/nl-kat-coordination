import pkgutil

import os

import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Tuple

from boefjes.plugins.models import (
    BoefjeResource,
    NormalizerResource,
    BOEFJES_DIR,
    BOEFJE_DEFINITION_FILE,
    NORMALIZER_DEFINITION_FILE,
    ENTRYPOINT_BOEFJES,
    ENTRYPOINT_NORMALIZERS,
    ModuleException,
)
from boefjes.katalogus.models import PluginType, Boefje, Normalizer, RESERVED_LOCAL_ID


logger = logging.getLogger(__name__)


class LocalPluginRepository:
    def __init__(self, path: Path):
        self.path = path

    def get_all(self) -> List[PluginType]:
        all_plugins = [self._boefje_to_plugin(boefje) for boefje in self.resolve_boefjes().values()]
        normalizers = [self._normalizer_to_plugin(normalizer) for normalizer in self.resolve_normalizers().values()]

        all_plugins += normalizers

        return all_plugins

    def by_id(self, plugin_id: str) -> Optional[PluginType]:
        boefjes = self.resolve_boefjes()

        if plugin_id in boefjes:
            return self._boefje_to_plugin(boefjes[plugin_id])

        normalizers = self.resolve_normalizers()

        if plugin_id in normalizers:
            return self._normalizer_to_plugin(normalizers[plugin_id])

    def schema(self, id_: str) -> Optional[Dict]:
        boefjes = self.resolve_boefjes()

        if id_ not in boefjes:
            return None

        path = boefjes[id_].path / "schema.json"

        if not path.exists():
            logger.debug(f"Did not find schema for boefje {boefjes[id_]=}")
            return None

        return json.loads(path.read_text())

    def cover_path(self, id_: str) -> Path:
        boefjes = self.resolve_boefjes()

        if id_ not in boefjes:
            return self.default_cover_path()

        boefje = boefjes[id_]
        path = boefje.path / "cover.jpg"

        if not path.exists():
            logger.debug(f"Did not find cover for boefje {boefje=}")
            return self.default_cover_path()

        logger.debug(f"Found cover for boefje {boefje=}")

        return path

    def default_cover_path(self) -> Path:
        return self.path / "default_cover.jpg"

    def description_path(self, id_: str) -> Optional[Path]:
        boefjes = self.resolve_boefjes()

        if id_ not in boefjes:
            return None

        return boefjes[id_].path / "description.md"

    def resolve_boefjes(self) -> Dict[str, BoefjeResource]:
        paths_and_packages = self._find_packages_in_path_containing_files([BOEFJE_DEFINITION_FILE, ENTRYPOINT_BOEFJES])
        boefje_resources = []

        for path, package in paths_and_packages:
            try:
                boefje_resources.append(BoefjeResource(path, package, RESERVED_LOCAL_ID))
            except ModuleException as exc:
                logger.exception(exc)

        return {resource.boefje.id: resource for resource in boefje_resources}

    def resolve_normalizers(self) -> Dict[str, NormalizerResource]:
        paths_and_packages = self._find_packages_in_path_containing_files(
            [NORMALIZER_DEFINITION_FILE, ENTRYPOINT_NORMALIZERS]
        )
        normalizer_resources = [
            NormalizerResource(path, package, RESERVED_LOCAL_ID) for path, package in paths_and_packages
        ]

        return {resource.normalizer.id: resource for resource in normalizer_resources}

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
        relative_path = str(package_dir.absolute()).replace(os.getcwd(), "")  # e.g. "/boefjes/plugins"

        return f"{relative_path[1:].replace('/', '.')}."  # Turns into "boefjes.plugins."

    @staticmethod
    def _boefje_to_plugin(boefje: BoefjeResource) -> Boefje:
        def_file = boefje.path / "boefje.json"
        def_obj = json.loads(def_file.read_text())
        def_obj["repository_id"] = RESERVED_LOCAL_ID

        return Boefje.parse_obj(def_obj)

    @staticmethod
    def _normalizer_to_plugin(normalizer: NormalizerResource) -> Normalizer:
        def_file = normalizer.path / "normalizer.json"
        def_obj = json.loads(def_file.read_text())
        def_obj["repository_id"] = RESERVED_LOCAL_ID

        return Normalizer.parse_obj(def_obj)


def get_local_repository():
    return LocalPluginRepository(BOEFJES_DIR)
