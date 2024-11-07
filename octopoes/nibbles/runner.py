from collections.abc import Callable
from datetime import datetime
from itertools import chain, product
from typing import TypeVar

from nibbles.definitions import NibbleDefinition, get_nibble_definitions
from octopoes.models import OOI
from octopoes.models.types import type_by_name
from octopoes.repositories.ooi_repository import OOIRepository
from octopoes.repositories.origin_parameter_repository import OriginParameterRepository
from octopoes.repositories.scan_profile_repository import ScanProfileRepository

T = TypeVar("T")
U = TypeVar("U")


def otype(ooi: OOI) -> type[OOI]:
    return type_by_name(ooi.get_ooi_type())


def mergewith(func: Callable[[set[T], set[T]], set[T]], d1: dict[U, set[T]], d2: dict[U, set[T]]) -> dict[U, set[T]]:
    return {k: func(d1.get(k, set()), d2.get(k, set())) for k in set(d1) | set(d2)}


class NibblesRunner:
    def __init__(
        self,
        ooi_repository: OOIRepository,
        scan_profile_repository: ScanProfileRepository,
        origin_parameter_repository: OriginParameterRepository,
    ):
        self.ooi_repository = ooi_repository
        self.scan_profile_repository = scan_profile_repository
        self.origin_parameter_repository = origin_parameter_repository
        self.objects_by_type_cache: dict[type[OOI], set[OOI]]
        self.update_nibbles()

    def _retrieve(self, types: set[type[OOI]], valid_time: datetime) -> None:
        cached_types = set(self.objects_by_type_cache)
        target_types = set(filter(lambda x: x not in cached_types, types))
        objects = self.ooi_repository.list_oois_by_object_types(target_types, valid_time)
        objects_by_type = {t: {x for x in objects if isinstance(otype(x), t)} for t in set(map(otype, objects))}
        self.objects_by_type_cache = mergewith(set.union, self.objects_by_type_cache, objects_by_type)

    def _run(self, ooi: OOI, valid_time: datetime) -> dict[str, set[OOI]]:
        retval: dict[str, set[OOI]] = {}
        target_nibbles = list(filter(lambda x: type(ooi) in x.signature, self.nibbles))
        self._retrieve(
            set(map(lambda x: x.ooi_type, chain.from_iterable(map(lambda x: x.signature, target_nibbles)))), valid_time
        )
        for nibble in target_nibbles:
            # TODO: filter OOI not abiding the parameters from radix
            radix = [self.objects_by_type_cache[sgn.ooi_type] for sgn in nibble.signature]
            results = set(
                filter(lambda ooi: ooi is not None, chain(map(nibble, filter(lambda x: ooi in x, product(*radix)))))
            )
            if results:
                retval |= {nibble.id: results}
        return retval

    def update_nibbles(self):
        self.nibbles: list[NibbleDefinition] = get_nibble_definitions()

    def _cleared(self, ooi: OOI, valid_time: datetime) -> bool:
        ooi_level = self.scan_profile_repository.get(ooi.reference, valid_time).level.value
        target_nibbles = list(filter(lambda x: type(ooi) in x.signature, self.nibbles))
        return any(nibble.min_scan_level < ooi_level for nibble in target_nibbles)

    def infer(self, stack: list[OOI], valid_time: datetime) -> dict[OOI, dict[str, set[OOI]]]:
        retval: dict[OOI, dict[str, set[OOI]]] = {}
        blockset = set(stack)
        self.objects_by_type_cache = {}
        if self._cleared(stack[-1], valid_time):
            while stack:
                ooi = stack.pop()
                self.objects_by_type_cache = mergewith(set.union, self.objects_by_type_cache, {otype(ooi): {ooi}})
                results = self._run(ooi, valid_time)
                if results:
                    blocks = set(chain.from_iterable(results.values()))
                    stack += list(filter(lambda ooi: ooi not in blockset, blocks))
                    blockset |= blocks
                    retval |= {ooi: results}
        return retval
