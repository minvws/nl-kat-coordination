import importlib
import pkgutil
from logging import getLogger
from pathlib import Path
from types import MethodType, ModuleType

from pydantic import BaseModel

from octopoes.models import OOI

NIBBLES_DIR = Path(__file__).parent
NIBBLE_ATTR_NAME = "NIBBLE"
NIBBLE_FUNC_NAME = "nibble"
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

    def __hash__(self):
        return hash(str(self.ooi_type) + self.relation_path if self.relation_path else "\0")


class NibbleDefinition:
    id: str
    signature: list[NibbleParameterDefinition]
    min_scan_level: int = 1
    default_enabled: bool = True
    config_ooi_relation_path: str | None = None
    payload: MethodType | None = None

    def __init__(
        self,
        name: str,
        signature: list,
        min_scan_level: int = 1,
        default_enabled: bool = True,
        config_ooi_relation_path: str | None = None,
    ):
        self.id = name
        self.signature = signature
        self.min_scan_level = min_scan_level
        self.default_enabled = default_enabled
        self.config_ooi_relation_path = config_ooi_relation_path

    def __call__(self, *_):
        if self.payload is None:
            raise NotImplementedError
        else:
            return self.payload(*_)


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
