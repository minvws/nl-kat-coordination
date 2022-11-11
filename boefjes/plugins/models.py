from importlib import import_module
from inspect import signature, isfunction

import json

from enum import Enum
from pathlib import Path
from typing import Set, Union, Protocol

from pydantic import BaseModel, StrictBytes

from boefjes.katalogus.models import Boefje, Normalizer

BOEFJES_DIR = Path(__file__).parent

BOEFJE_DEFINITION_FILE = "boefje.json"
NORMALIZER_DEFINITION_FILE = "normalizer.json"
ENTRYPOINT_BOEFJES = "main.py"
ENTRYPOINT_NORMALIZERS = "normalize.py"


class SCAN_LEVEL(Enum):
    L0 = 0
    L1 = 1
    L2 = 2
    L3 = 3
    L4 = 4


class ModuleException(Exception):
    """General error for modules"""


class Runnable(Protocol):
    def run(self, *args, **kwargs):
        raise NotImplementedError


class BoefjeResource:
    def __init__(self, path: Path, package: str, repository_id: str):
        self.path = path

        item = json.loads((path / BOEFJE_DEFINITION_FILE).read_text())
        self.boefje = Boefje(**item, repository_id=repository_id)

        import_statement = package + "." + ENTRYPOINT_BOEFJES.rstrip(".py")
        module: Runnable = import_module(import_statement)

        if not hasattr(module, "run") or not isfunction(module.run):
            raise ModuleException(f"Module {module} does not define a run function")

        if len(signature(module.run).parameters) != 1:
            raise ModuleException("Module entrypoint has wrong amount of parameters")

        self.module = module


class NormalizerResource:
    def __init__(self, path: Path, package: str, repository_id: str):
        self.path = path

        item = json.loads((path / NORMALIZER_DEFINITION_FILE).read_text())
        self.normalizer = Normalizer(**item, repository_id=repository_id)

        import_statement = package + "." + ENTRYPOINT_NORMALIZERS.rstrip(".py")
        module: Runnable = import_module(import_statement)

        if not hasattr(module, "run") or not isfunction(module.run):
            raise ModuleException(f"Module {module} does not define a run function")

        if len(signature(module.run).parameters) != 2:
            raise ModuleException("Module entrypoint has wrong amount of parameters")

        self.module = module


class RawData(BaseModel):
    data: Union[StrictBytes, str]
    mime_types: Set[str]
