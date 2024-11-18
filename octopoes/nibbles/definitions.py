import importlib
import pkgutil
from collections.abc import Iterable
from pathlib import Path
from types import MethodType, ModuleType

import structlog
from pydantic import BaseModel

from octopoes.models import OOI

NIBBLES_DIR = Path(__file__).parent
NIBBLE_ATTR_NAME = "NIBBLE"
NIBBLE_FUNC_NAME = "nibble"
logger = structlog.get_logger(__name__)


class NibbleParameter(BaseModel):
    object_type: type
    parser: str = "[]"

    def __eq__(self, other):
        if isinstance(other, NibbleParameter):
            return vars(self) == vars(other)
        elif isinstance(other, type):
            return self.object_type == other
        else:
            return False


class NibbleDefinition:
    id: str
    signature: list[NibbleParameter]
    query: str | None = None
    min_scan_level: int = 1
    default_enabled: bool = True
    config_ooi_relation_path: str | None = None
    payload: MethodType | None = None

    def __init__(
        self,
        name: str,
        signature: list[NibbleParameter],
        query: str | None = None,
        min_scan_level: int = 1,
        default_enabled: bool = True,
        config_ooi_relation_path: str | None = None,
    ):
        self.id = name
        self.signature = signature
        self.query = query
        self.min_scan_level = min_scan_level
        self.default_enabled = default_enabled
        self.config_ooi_relation_path = config_ooi_relation_path

    def __call__(self, args: Iterable[OOI]) -> OOI | Iterable[OOI | None] | None:
        if self.payload is None:
            raise NotImplementedError
        else:
            return self.payload(*args)


def get_nibble_definitions() -> list[NibbleDefinition]:
    nibble_definitions = []

    for package in pkgutil.walk_packages([str(NIBBLES_DIR)]):
        if package.name in ["definitions", "runner"]:
            continue

        try:
            module: ModuleType = importlib.import_module(".nibble", f"{NIBBLES_DIR.name}.{package.name}")

            if hasattr(module, NIBBLE_ATTR_NAME):
                nibble_definition: NibbleDefinition = getattr(module, NIBBLE_ATTR_NAME)

                try:
                    payload: ModuleType = importlib.import_module(
                        f".{package.name}", f"{NIBBLES_DIR.name}.{package.name}"
                    )
                    if hasattr(payload, NIBBLE_FUNC_NAME):
                        nibble_definition.payload = getattr(payload, NIBBLE_FUNC_NAME)
                    else:
                        logger.warning('module "%s" has no function %s', package.name, NIBBLE_FUNC_NAME)

                except ModuleNotFoundError:
                    logger.warning('package "%s" has no function nibble', package.name)

                nibble_definitions.append(nibble_definition)

            else:
                logger.warning('module "%s" has no attribute %s', package.name, NIBBLE_ATTR_NAME)

        except ModuleNotFoundError:
            logger.warning('package "%s" has no module nibble', package.name)

    return nibble_definitions
