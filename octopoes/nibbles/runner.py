from collections.abc import Callable, Iterable
from datetime import datetime
from itertools import chain
from typing import TypeVar

from nibbles.definitions import NibbleDefinition, get_nibble_definitions
from octopoes.models import OOI
from octopoes.models.types import type_by_name
from octopoes.repositories.ooi_repository import OOIRepository
from octopoes.repositories.scan_profile_repository import ScanProfileRepository

T = TypeVar("T")
U = TypeVar("U")


def object_type(ooi: OOI) -> type[OOI]:
    return type_by_name(ooi.get_ooi_type())


def merge_with(func: Callable[[set[T], set[T]], set[T]], d1: dict[U, set[T]], d2: dict[U, set[T]]) -> dict[U, set[T]]:
    return {k: func(d1.get(k, set()), d2.get(k, set())) for k in set(d1) | set(d2)}


def flatten(items: Iterable[OOI | Iterable[OOI | None] | None]) -> Iterable[OOI]:
    for item in items:
        if isinstance(item, OOI):
            yield item
        elif item is None:
            continue
        else:
            yield from flatten(item)


class NibblesRunner:
    def __init__(self, ooi_repository: OOIRepository, scan_profile_repository: ScanProfileRepository):
        self.ooi_repository = ooi_repository
        self.scan_profile_repository = scan_profile_repository
        self.update_nibbles()

    def update_nibbles(self):
        self.nibbles: list[NibbleDefinition] = get_nibble_definitions()

    def _run(self, ooi: OOI, valid_time: datetime) -> dict[str, set[OOI]]:
        retval: dict[str, set[OOI]] = {}
        for nibble in filter(lambda x: type(ooi) in x.signature, self.nibbles):
            if nibble.query is None:
                args = [[ooi]]
            else:
                raise NotImplementedError
                args = self.ooi_repository.query(nibble.query, valid_time)
            data = (nibble(arg) for arg in args if ooi in arg)
            results = {obj for obj in flatten(data)}
            if results:
                retval |= {nibble.id: results}
        return retval

    def _cleared(self, ooi: OOI, valid_time: datetime) -> bool:
        ooi_level = self.scan_profile_repository.get(ooi.reference, valid_time).level.value
        target_nibbles = filter(lambda x: type(ooi) in x.signature, self.nibbles)
        return any(nibble.min_scan_level < ooi_level for nibble in target_nibbles)

    def infer(self, stack: list[OOI], valid_time: datetime) -> dict[OOI, dict[str, set[OOI]]]:
        # TODO: check for initial clearance
        retval: dict[OOI, dict[str, set[OOI]]] = {}
        blockset = set(stack)
        if stack and self._cleared(stack[-1], valid_time):
            while stack:
                ooi = stack.pop()
                results = self._run(ooi, valid_time)
                if results:
                    blocks = set(chain.from_iterable(results.values()))
                    stack += [ooi for ooi in blocks if ooi not in blockset]
                    blockset |= blocks
                    retval |= {ooi: results}
        return retval
