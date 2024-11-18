from collections.abc import Callable, Iterable
from datetime import datetime
from itertools import product
from typing import TypeVar

from jmespath import search

from nibbles.definitions import NibbleDefinition, get_nibble_definitions
from octopoes.models import OOI
from octopoes.models.origin import NibbleOrigin, OriginType
from octopoes.models.types import type_by_name
from octopoes.repositories.ooi_repository import OOIRepository
from octopoes.repositories.origin_repository import OriginRepository
from octopoes.repositories.scan_profile_repository import ScanProfileRepository

T = TypeVar("T")
U = TypeVar("U")


def ooi_type(ooi: OOI) -> type[OOI]:
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
    def __init__(
        self,
        ooi_repository: OOIRepository,
        origin_repository: OriginRepository,
        scan_profile_repository: ScanProfileRepository,
    ):
        self.ooi_repository = ooi_repository
        self.origin_repository = origin_repository
        self.scan_profile_repository = scan_profile_repository
        self.update_nibbles()

    def update_nibbles(self):
        self.nibbles: list[NibbleDefinition] = get_nibble_definitions()

    def objectify(self, t: type, obj: dict | list):
        if issubclass(t, OOI):
            return self.ooi_repository.deserialize(obj)
        else:
            if isinstance(obj, dict):
                return t(**obj)
            else:
                return t(*obj)

    def _arguments(self, nibble: NibbleDefinition, ooi: OOI, valid_time: datetime) -> Iterable[Iterable]:
        if nibble.query is None:
            return [[ooi]]
        else:
            query = self.ooi_repository.raw_query(nibble.query, valid_time)
            parsed_data = [
                {ooi, *[self.objectify(sgn.object_type, obj) for obj in search(sgn.parser, query)]}
                if isinstance(ooi, sgn.object_type)
                else {self.objectify(sgn.object_type, obj) for obj in search(sgn.parser, query)}
                for sgn in nibble.signature
            ]
            return list(product(*parsed_data))

    def _run(self, ooi: OOI, valid_time: datetime) -> dict[str, list[tuple[list[OOI], set[OOI]]]]:
        return_value: dict[str, list[tuple[list[OOI], set[OOI]]]] = {}
        for nibble in filter(lambda x: type(ooi) in x.signature, self.nibbles):
            args = self._arguments(nibble, ooi, valid_time)
            results = [(list(arg), set(flatten([nibble(arg)]))) for arg in args]
            if results:
                return_value |= {nibble.id: results}
                # TODO: we could cache the writes for single OOI nibbles
                self._write({ooi: return_value}, valid_time)
        return return_value

    def _cleared(self, ooi: OOI, valid_time: datetime) -> bool:
        ooi_level = self.scan_profile_repository.get(ooi.reference, valid_time).level.value
        target_nibbles = filter(lambda x: type(ooi) in x.signature, self.nibbles)
        return any(nibble.min_scan_level < ooi_level for nibble in target_nibbles)

    def _write(self, inferences: dict[OOI, dict[str, list[tuple[list[OOI], set[OOI]]]]], valid_time: datetime):
        for source_ooi, results in inferences.items():
            self.ooi_repository.save(source_ooi, valid_time)
            for nibble_id, run_result in results.items():
                for arg, result in run_result:
                    nibble_origin = NibbleOrigin(
                        method=nibble_id,
                        origin_type=OriginType.NIBBLE,
                        result=[ooi.reference for ooi in result],
                        source=source_ooi.reference,
                        parameters=[ooi.reference for ooi in arg],
                    )
                    for ooi in result:
                        self.ooi_repository.save(ooi, valid_time=valid_time)
                    self.origin_repository.save(nibble_origin, valid_time=valid_time)

    def infer(self, stack: list[OOI], valid_time: datetime) -> dict[OOI, dict[str, list[tuple[list[OOI], set[OOI]]]]]:
        inferences: dict[OOI, dict[str, list[tuple[list[OOI], set[OOI]]]]] = {}
        blockset = set(stack)
        if stack and self._cleared(stack[-1], valid_time):
            while stack:
                ooi = stack.pop()
                results = self._run(ooi, valid_time)
                if results:
                    blocks = set.union(*[ooiset for result in results.values() for _, ooiset in result])
                    stack += [o for o in blocks if o not in blockset]
                    blockset |= blocks
                    inferences |= {ooi: results}
        return inferences
