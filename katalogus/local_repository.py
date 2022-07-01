import logging
from pathlib import Path
from typing import List, Optional

from boefjes.models import (
    Boefje as BoefjeModel,
    Normalizer as NormalizerModel,
    BOEFJES_DIR,
)
from katalogus.boefjes import resolve_boefjes, resolve_normalizers
from katalogus.models import PluginType, Boefje, Normalizer


logger = logging.getLogger(__name__)


class LocalPluginRepository:
    RESERVED_ID = "LOCAL"

    def __init__(self, path: Path):
        self.path = path

    def get_all(self) -> List[PluginType]:
        all_plugins = [
            self._boefje_to_plugin(boefje)
            for boefje in resolve_boefjes(self.path).values()
        ]
        normalizers = [
            self._normalizer_to_plugin(normalizer)
            for normalizer in resolve_normalizers(self.path).values()
        ]

        all_plugins += normalizers

        return all_plugins

    def cover_path(self, id_: str) -> Path:
        boefje = resolve_boefjes(self.path)[id_]
        parent, _ = boefje.module.split(".", maxsplit=1)

        path = self.path / parent / "cover.png"

        if not path.exists():
            logger.info(f"Did not find cover for boefje {boefje=}")
            return self.default_cover_path()

        logger.info(f"Found cover for boefje {boefje=}")

        return path

    def default_cover_path(self):
        return self.path / "default_cover.png"

    def description_path(self, id_: str) -> Optional[Path]:
        boefjes = resolve_boefjes(self.path)

        if id_ not in boefjes:
            return None

        boefje = boefjes[id_]
        parent, _ = boefje.module.split(".", maxsplit=1)

        return self.path / parent / "description.md"

    @staticmethod
    def _boefje_to_plugin(boefje: BoefjeModel) -> Boefje:
        return Boefje(
            id=boefje.id,
            name=boefje.name,
            repository_id=LocalPluginRepository.RESERVED_ID,
            scan_level=boefje.scan_level.value,
            consumes=boefje.consumes,
            produces=list(boefje.produces),
            description=boefje.description,
        )

    @staticmethod
    def _normalizer_to_plugin(normalizer: NormalizerModel) -> Normalizer:
        return Normalizer(
            id=normalizer.name,
            name=normalizer.name,
            repository_id=LocalPluginRepository.RESERVED_ID,
            consumes=normalizer.consumes.copy(),
            produces=[],
        )


def get_local_repository():
    return LocalPluginRepository(BOEFJES_DIR)
