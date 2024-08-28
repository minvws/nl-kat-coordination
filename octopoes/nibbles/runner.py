from collections.abc import Callable
from datetime import datetime
from itertools import chain, product
from typing import TypeVar

from nibbles.definitions import NibbleDefinition, get_nibble_definitions
from octopoes.models import OOI
from octopoes.models.types import type_by_name
from octopoes.repositories.ooi_repository import OOIRepository

T = TypeVar("T")
U = TypeVar("U")


def otype(ooi: OOI) -> type[OOI]:
    return type_by_name(ooi.get_ooi_type())


def mergewith(func: Callable[[set[T], set[T]], set[T]], d1: dict[U, set[T]], d2: dict[U, set[T]]) -> dict[U, set[T]]:
    return {k: func(d1[k], d2[k]) for k in set(d1) | set(d2)}


class NibblesRunner:
    def __init__(self, ooi_repository: OOIRepository):
        self.ooi_repository = ooi_repository
        self.objects_by_type_cache: dict[type[OOI], set[OOI]]
        self.update_nibbles()

    # TODO: path query for relation path (in Parameter definitions)
    def _retrieve(self, types: set[type[OOI]], valid_time: datetime) -> None:
        cached_types = set(self.objects_by_type_cache)
        target_types = set(filter(lambda x: x not in cached_types, types))
        # FIXME: this does not account for type collides
        objects = self.ooi_repository.list_oois_by_object_types(target_types, valid_time)
        objects_by_type = {t: {x for x in objects if isinstance(otype(x), t)} for t in set(map(otype, objects))}
        self.objects_by_type_cache = mergewith(set.union, self.objects_by_type_cache, objects_by_type)

    def _run(self, ooi: OOI, valid_time: datetime) -> dict[str, set[OOI]]:
        retval: dict[str, set[OOI]] = {}
        target_nibbles = list(filter(lambda x: type(ooi) in x.signature, self.nibbles))
        self._retrieve(set(chain.from_iterable(map(lambda x: x.signature, target_nibbles))), valid_time)
        for nibble in target_nibbles:
            radix = [self.objects_by_type_cache[sgn.ooi_type] for sgn in nibble.signature]
            retval |= {nibble.id: nibble(*list(filter(lambda x: ooi in x, product(radix))))}
        return retval

    def update_nibbles(self):
        self.nibbles: list[NibbleDefinition] = get_nibble_definitions()

    def infer(self, stack: list[OOI], valid_time: datetime) -> dict[OOI, dict[str, set[OOI]]]:
        retval: dict[OOI, dict[str, set[OOI]]] = {}
        self.objects_by_type_cache = {}
        while stack:
            ooi = stack.pop()
            self.objects_by_type_cache = mergewith(set.union, self.objects_by_type_cache, {otype(ooi): {ooi}})
            retval |= {ooi: self._run(ooi, valid_time)}

        return retval
