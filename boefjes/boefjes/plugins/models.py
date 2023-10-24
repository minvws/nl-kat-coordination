import hashlib
from enum import Enum
from importlib import import_module
from inspect import isfunction, signature
from pathlib import Path
from typing import Protocol, Set

from boefjes.job_models import BoefjeMeta
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
        self.boefje: Boefje = Boefje.parse_file(path / BOEFJE_DEFINITION_FILE)
        self.boefje.runnable_hash = get_runnable_hash(self.path)
        self.boefje.mime_types.union(set(_default_mime_types(self.boefje)))
        self.module = get_runnable_module_from_package(package, ENTRYPOINT_BOEFJES, parameter_count=1)


class NormalizerResource:
    """Represents a Normalizer package that we can run. Throws a ModuleException if any validation fails."""

    def __init__(self, path: Path, package: str):
        self.path = path
        self.normalizer = Normalizer.parse_file(path / NORMALIZER_DEFINITION_FILE)
        self.normalizer.consumes.append(f"normalizer/{self.normalizer.id}")
        self.module = get_runnable_module_from_package(package, ENTRYPOINT_NORMALIZERS, parameter_count=2)


def get_runnable_hash(path: Path) -> str:
    """Returns sha256(file1 + file2 + ...) of all files in the given path."""

    folder_hash = hashlib.sha256()

    for file in sorted(path.glob("**/*")):
        # Note that the hash does not include *.pyc files
        # Thus there may be a desync between the source code and the cached, compiled bytecode
        if file.is_file() and file.suffix != ".pyc":
            with file.open("rb") as f:
                while chunk := f.read(32768):
                    folder_hash.update(chunk)

    return folder_hash.hexdigest()


def _default_meta_mime_types(boefje_meta: BoefjeMeta) -> Set[str]:
    mime_types = _default_mime_types(boefje_meta.boefje)
    mime_types.add(f"boefje/{boefje_meta.boefje.id}-{boefje_meta.parameterized_arguments_hash}")

    if boefje_meta.boefje.version is not None:
        mime_types = mime_types.add(
            f"boefje/{boefje_meta.boefje.id}-{boefje_meta.parameterized_arguments_hash}-{boefje_meta.boefje.version}",
        )

    return mime_types


def _default_mime_types(boefje: Boefje):
    mime_types = {boefje.id, f"boefje/{boefje.id}"}

    if boefje.version is not None:
        mime_types = mime_types.union({f"boefje/{boefje.id}-{boefje.version}"})

    return mime_types
