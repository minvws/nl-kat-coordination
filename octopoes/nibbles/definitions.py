import importlib
import pkgutil
from functools import lru_cache
from logging import getLogger
from pathlib import Path
from types import ModuleType

from pydantic import BaseModel

from octopoes.models import OOI

NIBBLES_DIR = Path(__file__).parent
NIBBLE_ATTR_NAME = "NIBBLE"
logger = getLogger(__name__)


class NibbleParameterDefinition(BaseModel):
    ooi_type: type[OOI]
    relation_path: str | None = None

    def __eq__(self, other):
        if isinstance(other, NibbleParameterDefinition):
            return vars(self) == vars(other)
        elif isinstance(other, type):
            return self.ooi_type == other
        else:
            return False


class NibbleDefinition(BaseModel):
    id: str
    signature: list[NibbleParameterDefinition]
    min_scan_level: int = 1
    default_enabled: bool = True
    config_ooi_relation_path: str | None = None

    def __call__(self, *_):
        raise NotImplementedError


@lru_cache(maxsize=32)
def get_nibble_definitions() -> list[NibbleDefinition]:
    nibble_definitions = []

    for package in pkgutil.walk_packages([str(NIBBLES_DIR)]):
        if package.name in ["definitions", "runner"]:
            continue

        try:
            module: ModuleType = importlib.import_module(".nibble", f"{NIBBLES_DIR.name}.{package.name}")

            if hasattr(module, NIBBLE_ATTR_NAME):
                nibble_definition: NibbleDefinition = getattr(module, NIBBLE_ATTR_NAME)
                nibble_definitions.append(nibble_definition)

            else:
                logger.warning('module "%s" has no attribute %s', package.name, NIBBLE_ATTR_NAME)

        except ModuleNotFoundError:
            logger.warning('package "%s" has no module %s', package.name, "nibble")

    return nibble_definitions
