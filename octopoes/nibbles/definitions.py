import importlib
import inspect
import pkgutil
from collections.abc import Callable, Iterable
from pathlib import Path
from types import MethodType, ModuleType
from typing import Any

import structlog
from pydantic import BaseModel
from xxhash import xxh3_128_hexdigest as xxh3

from octopoes.models import OOI, Reference

NIBBLES_DIR = Path(__file__).parent
NIBBLE_ATTR_NAME = "NIBBLE"
NIBBLE_FUNC_NAME = "nibble"
logger = structlog.get_logger(__name__)


class NibbleParameter(BaseModel):
    object_type: type[Any]
    parser: str = "[]"
    optional: bool = False

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
    enabled: bool = True
    _payload: MethodType | None = None
    _checksum: str | None = None

    def __call__(self, args: Iterable[OOI]) -> OOI | Iterable[OOI | None] | None:
        if self._payload is None:
            raise NotImplementedError
        else:
            return self._payload(*args)

    def __hash__(self):
        return hash(self.id)

    @property
    def _ini(self) -> dict[str, Any]:
        return {"id": self.id, "enabled": self.enabled, "checksum": self._checksum}

    @property
    def triggers(self) -> set[type[OOI]]:
        return {sgn.object_type for sgn in self.signature if issubclass(sgn.object_type, OOI)}


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
                        nibble_definition._checksum = xxh3(inspect.getsource(module) + inspect.getsource(payload))
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
