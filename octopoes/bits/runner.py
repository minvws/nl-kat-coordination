from importlib import import_module
from inspect import signature, isfunction
from typing import List, Iterator, Any, cast, Protocol

from bits.definitions import BitDefinition
from octopoes.models import OOI


class ModuleException(Exception):
    """General error for modules"""


class Runnable(Protocol):
    def run(self, *args, **kwargs) -> Any:
        ...


class BitRunner:
    def __init__(self, bit_definition: BitDefinition):
        self.module = bit_definition.module

    def run(self, *args, **kwargs) -> List[OOI]:
        module = import_module(self.module)
        module = cast(Runnable, module)

        if not hasattr(module, "run") or not isfunction(module.run):
            raise ModuleException(f"Module {module} does not define a run function")

        if signature(module.run).return_annotation != BIT_SIGNATURE.return_annotation:
            raise ModuleException(
                f"Invalid run function return annotation, expected '{BIT_SIGNATURE.return_annotation}'"
            )
        return list(module.run(*args, **kwargs))

    def __str__(self):
        return f"BitRunner {self.module}"


def _bit_run_signature(input_ooi: OOI, additional_oois: List[OOI]) -> Iterator[OOI]:
    ...


BIT_SIGNATURE = signature(_bit_run_signature)
