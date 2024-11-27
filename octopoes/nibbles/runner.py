import json
from collections.abc import Callable, Iterable
from datetime import datetime
from typing import TypeVar

from xxhash import xxh3_128_hexdigest as xxh3  # INFO: xxh3_64_hexdigest is faster but hash more collision probabilities

from nibbles.definitions import NibbleDefinition, get_nibble_definitions
from octopoes.models import OOI
from octopoes.models.origin import Origin, OriginType
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


def nibble_hasher(data: Iterable) -> str:
    return xxh3(
        "".join(
            [
                json.dumps(json.loads(ooi.model_dump_json()), sort_keys=True)
                if isinstance(ooi, OOI)
                else json.dumps(ooi, sort_keys=True)
                for ooi in data
            ]
        )
    )


class NibblesRunner:
    def __init__(
        self,
        ooi_repository: OOIRepository,
        origin_repository: OriginRepository,
        scan_profile_repository: ScanProfileRepository,
        perform_writes: bool = True,
    ):
        self.ooi_repository = ooi_repository
        self.origin_repository = origin_repository
        self.scan_profile_repository = scan_profile_repository
        self.perform_writes = perform_writes
        self.update_nibbles()

    def update_nibbles(self):
        self.nibbles: dict[str, NibbleDefinition] = get_nibble_definitions()

    def _run(self, ooi: OOI, valid_time: datetime) -> dict[str, dict[tuple, set[OOI]]]:
        return_value: dict[str, dict[tuple, set[OOI]]] = {}
        nibblettes = self.origin_repository.list_origins(
            valid_time, origin_type=OriginType.NIBBLETTE, parameters_references=[ooi.reference]
        )
        if nibblettes:
            for nibblette in nibblettes:
                # INFO: we do not strictly need this if statement because OriginType.NIBBLETTES \
                # always have parameters_references but it makes the linters super happy
                if nibblette.parameters_references:
                    nibble = self.nibbles[nibblette.method]
                    args = self.ooi_repository.nibble_query(
                        ooi,
                        nibble,
                        valid_time,
                        nibblette.parameters_references
                        if nibble.query is not None and nibble.query.count("$") > 0
                        else [],
                    )
                    results = {
                        tuple(arg): set(flatten([nibble(arg)]))
                        for arg in args
                        if nibblette.parameters_hash != nibble_hasher(arg)
                    }
                    return_value |= {nibble.id: results}
        else:
            for nibble in filter(lambda x: type(ooi) in x.signature, self.nibbles.values()):
                args = self.ooi_repository.nibble_query(ooi, nibble, valid_time)
                results = {tuple(arg): set(flatten([nibble(arg)])) for arg in args}
                return_value |= {nibble.id: results}
        # TODO: we could cache the writes for single OOI nibbles
        self._write({ooi: return_value}, valid_time)
        return return_value

    def _cleared(self, ooi: OOI, valid_time: datetime) -> bool:
        ooi_level = self.scan_profile_repository.get(ooi.reference, valid_time).level.value
        target_nibbles = filter(lambda x: type(ooi) in x.signature, self.nibbles.values())
        return any(nibble.min_scan_level < ooi_level for nibble in target_nibbles)

    def _write(self, inferences: dict[OOI, dict[str, dict[tuple, set[OOI]]]], valid_time: datetime):
        if self.perform_writes:
            for source_ooi, results in inferences.items():
                self.ooi_repository.save(source_ooi, valid_time)
                for nibble_id, run_result in results.items():
                    for arg, result in run_result.items():
                        nibble_origin = Origin(
                            method=nibble_id,
                            origin_type=OriginType.NIBBLETTE,
                            source=source_ooi.reference,
                            result=[ooi.reference for ooi in result],
                            parameters_hash=nibble_hasher(arg),
                            # TODO: What to do if a is not an OOI?
                            parameters_references=[a.reference for a in arg if isinstance(a, OOI)],
                        )
                        for ooi in result:
                            self.ooi_repository.save(ooi, valid_time=valid_time)
                        self.origin_repository.save(nibble_origin, valid_time=valid_time)

    def infer(self, stack: list[OOI], valid_time: datetime) -> dict[OOI, dict[str, dict[tuple, set[OOI]]]]:
        inferences: dict[OOI, dict[str, dict[tuple, set[OOI]]]] = {}
        blockset = set(stack)
        if stack and self._cleared(stack[-1], valid_time):
            while stack:
                ooi = stack.pop()
                results = self._run(ooi, valid_time)
                if results:
                    blocks = set.union(*[ooiset for result in results.values() for _, ooiset in result.items()])
                    stack += [o for o in blocks if o not in blockset]
                    blockset |= blocks
                    inferences |= {ooi: results}
        return inferences
