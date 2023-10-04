import importlib
import pkgutil
from functools import lru_cache
from logging import getLogger
from pathlib import Path
from types import ModuleType
from typing import Dict, List, Optional, Type

from pydantic import BaseModel

from octopoes.models import OOI

BITS_DIR = Path(__file__).parent
BIT_ATTR_NAME = "BIT"
logger = getLogger(__name__)


class BitParameterDefinition(BaseModel):
    ooi_type: Type[OOI]
    relation_path: str


class BitDefinition(BaseModel):
    id: str
    consumes: Type[OOI]
    parameters: List[BitParameterDefinition]
    module: str
    min_scan_level: int = 1
    default_enabled: bool = True
    config_ooi_relation_path: Optional[str] = None


@lru_cache(maxsize=32)
def get_bit_definitions() -> Dict[str, BitDefinition]:
    bit_definitions = {}

    for package in pkgutil.walk_packages([str(BITS_DIR)]):
        if package.name in ["definitions", "runner"]:
            continue

        try:
            module: ModuleType = importlib.import_module(".bit", f"{BITS_DIR.name}.{package.name}")

            if hasattr(module, BIT_ATTR_NAME):
                bit_definition: BitDefinition = getattr(module, BIT_ATTR_NAME)
                bit_definitions[bit_definition.id] = bit_definition

            else:
                logger.warning('module "%s" has no attribute %s', package.name, BIT_ATTR_NAME)

        except ModuleNotFoundError:
            logger.warning('package "%s" has no module %s', package.name, "bit")

    return bit_definitions
