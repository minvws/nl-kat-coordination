import importlib
import logging
import pkgutil
from pathlib import Path
from types import ModuleType
from typing import Dict, Set, List

from pydantic import BaseModel, Field, Extra

from boefjes.models import Boefje, Normalizer


class BoefjeResource(BaseModel):
    """Represents a Boefje as viewed from the Katalogus API, derived from a main Boefje class"""

    id: str
    name: str
    description: str
    consumes: Set[str] = Field(default_factory=set)
    produces: Set[str] = Field(default_factory=set)
    scan_level: int

    class Config:
        extra = Extra.forbid


def resolve_boefjes(package_dir: Path) -> Dict[str, Boefje]:
    packages = list(pkgutil.walk_packages([str(package_dir)]))

    modules_attrs = parse_module_attribute(
        package_dir, [package for package in packages if package.ispkg], "BOEFJES"
    )
    boefjes: Dict[str, Boefje] = {}

    for boefje_list in modules_attrs:
        boefjes.update({boefje.id: boefje for boefje in boefje_list})

    return boefjes


def resolve_normalizers(package_dir: Path) -> Dict[str, Normalizer]:
    packages = list(pkgutil.walk_packages([str(package_dir)]))

    modules_attrs = parse_module_attribute(
        package_dir, [package for package in packages if package.ispkg], "NORMALIZERS"
    )
    normalizers: Dict[str, Normalizer] = {}

    for normalizer_list in modules_attrs:
        normalizers.update(
            {normalizer.name: normalizer for normalizer in normalizer_list}
        )

    return normalizers


def parse_module_attribute(package_dir, packages, attr: str) -> List:
    modules_attrs = []

    for package in packages:
        try:
            module: ModuleType = importlib.import_module(
                ".boefje", f"{package_dir.name}.{package.name}"
            )

            if hasattr(module, attr):
                if attr == "BOEFJES" and not getattr(
                    getattr(module, attr)[0], "module"
                ):
                    getattr(module, attr)[0].module = package.name + ".main"
                modules_attrs.append(getattr(module, attr))

        except ModuleNotFoundError:
            logging.warning('module "%s" has no attribute %s', package.name, attr)

    return modules_attrs


def to_resource(boefje: Boefje) -> BoefjeResource:
    return BoefjeResource(
        id=boefje.id,
        name=boefje.name,
        description=boefje.description,
        consumes=boefje.consumes,
        produces=boefje.produces,
        scan_level=boefje.scan_level.value,
    )
