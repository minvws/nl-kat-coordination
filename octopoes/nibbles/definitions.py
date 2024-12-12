import importlib
import pkgutil
from collections.abc import Callable, Iterable
from pathlib import Path
from types import MethodType, ModuleType
from typing import Any

import structlog
from pydantic import BaseModel

from octopoes.models import OOI, Reference

NIBBLES_DIR = Path(__file__).parent
NIBBLE_ATTR_NAME = "NIBBLE"
NIBBLE_FUNC_NAME = "nibble"
logger = structlog.get_logger(__name__)


class NibbleParameter(BaseModel):
    object_type: type[Any]
    parser: str = "[]"

    def __eq__(self, other):
        if isinstance(other, NibbleParameter):
            return vars(self) == vars(other)
        elif isinstance(other, type):
            return self.object_type == other
        else:
            return False


class NibbleDefinition(BaseModel):
    id: str
    signature: list[NibbleParameter]
    query: str | Callable[[list[Reference | None]], str] | None = None
    _payload: MethodType | None = None

    def __call__(self, args: Iterable[OOI]) -> OOI | Iterable[OOI | None] | None:
        if self._payload is None:
            raise NotImplementedError
        else:
            return self._payload(*args)

    def __hash__(self):
        return hash(self.id)


def get_nibble_definitions() -> dict[str, NibbleDefinition]:
    nibble_definitions = {}

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
                        nibble_definition._payload = getattr(payload, NIBBLE_FUNC_NAME)
                    else:
                        logger.warning('module "%s" has no function %s', package.name, NIBBLE_FUNC_NAME)

                except ModuleNotFoundError:
                    logger.warning('package "%s" has no function nibble', package.name)

                nibble_definitions[nibble_definition.id] = nibble_definition

            else:
                logger.warning('module "%s" has no attribute %s', package.name, NIBBLE_ATTR_NAME)

        except ModuleNotFoundError:
            logger.warning('package "%s" has no module nibble', package.name)

    return nibble_definitions
