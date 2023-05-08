from enum import Enum
from importlib import import_module
from inspect import isfunction, signature
from pathlib import Path
from typing import Protocol

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


def get_runnable_module_from_package(package: str, module_file: str, *, parameter_count: int) -> Runnable:
    import_statement = f"{package}.{module_file.rstrip('.py')}"

    try:
        module = import_module(import_statement)
    except Exception as e:
        raise ModuleException(f"Cannot import module {import_statement}") from e

    if not hasattr(module, "run") or not isfunction(module.run):
        raise ModuleException(f"Module {module} does not define a run function")

    if len(signature(module.run).parameters) != parameter_count:
        raise ModuleException("Module entrypoint has wrong amount of parameters")

    return module


class BoefjeResource:
    """Represents a Boefje package that we can run. Throws a ModuleException if any validation fails."""

    def __init__(self, path: Path, package: str):
        self.path = path
        self.boefje = Boefje.parse_file(path / BOEFJE_DEFINITION_FILE)
        self.module = get_runnable_module_from_package(package, ENTRYPOINT_BOEFJES, parameter_count=1)


class NormalizerResource:
    """Represents a Normalizer package that we can run. Throws a ModuleException if any validation fails."""

    def __init__(self, path: Path, package: str):
        self.path = path
        self.normalizer = Normalizer.parse_file(path / NORMALIZER_DEFINITION_FILE)
        self.module = get_runnable_module_from_package(package, ENTRYPOINT_NORMALIZERS, parameter_count=2)
