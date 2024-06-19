import json
from collections.abc import Iterator
from datetime import datetime
from importlib import import_module
from inspect import isfunction, signature
from typing import Any, Protocol

from pydantic import JsonValue, TypeAdapter

from bits.definitions import BitDefinition
from octopoes.config.settings import CACHE_BITS
from octopoes.models import OOI


class ModuleException(Exception):
    """General error for modules"""


class Runnable(Protocol):
    def run(self, *args, **kwargs) -> Any: ...


class BitRunner:
    def __init__(self, bit_definition: BitDefinition):
        self.module = bit_definition.module
        self.cache_lifetime = bit_definition.cache_lifetime
        self.bit_cache: dict[str, tuple[list[OOI], datetime]] = {}

    def _purge(self) -> None:
        now = datetime.now()
        map(self.bit_cache.pop, [key for key, data in self.bit_cache.items() if now - data[1] > self.cache_lifetime])

    def _bit_cache_key(self, source: OOI, parameters: list[OOI], config: dict[str, JsonValue]) -> str:
        try:
            serialized_ooi = str(TypeAdapter(list[OOI]).dump_json(parameters))
            return source.model_dump_json() + serialized_ooi + json.dumps(config)
        except Exception:
            return str(datetime.now())

    def run(self, source: OOI, parameters: list[OOI], config: dict[str, JsonValue]) -> list[OOI]:
        module = import_module(self.module)

        if not hasattr(module, "run") or not isfunction(module.run):
            raise ModuleException(f"Module {module} does not define a run function")

        if signature(module.run).return_annotation != BIT_SIGNATURE.return_annotation:
            raise ModuleException(
                f"Invalid run function return annotation, expected '{BIT_SIGNATURE.return_annotation}'"
            )

        if CACHE_BITS:
            self._purge()
            key = self._bit_cache_key(source, parameters, config)
            if key not in self.bit_cache:
                data = list(module.run(source, parameters, config=config))
                self.bit_cache[key] = (data, datetime.now())
            return self.bit_cache[key][0]
        else:
            return list(module.run(source, parameters, config=config))

    def __str__(self):
        return f"BitRunner {self.module}"


def _bit_run_signature(input_ooi: OOI, additional_oois: list[OOI], config: dict[str, Any]) -> Iterator[OOI]:
    yield input_ooi


BIT_SIGNATURE = signature(_bit_run_signature)
