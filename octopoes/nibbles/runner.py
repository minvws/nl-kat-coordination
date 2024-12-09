import json
from collections.abc import Callable, Iterable
from datetime import datetime
from typing import Any, TypeVar

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


def merge_results(
    d1: dict[OOI, dict[str, dict[tuple[Any, ...], set[OOI]]]], d2: dict[OOI, dict[str, dict[tuple[Any, ...], set[OOI]]]]
) -> dict[OOI, dict[str, dict[tuple[Any, ...], set[OOI]]]]:
    return {
        key: {
            nibble_id: {
                arg: set(d1.get(key, {}).get(nibble_id, {}).get(arg, set()))
                | set(d2.get(key, {}).get(nibble_id, {}).get(arg, set()))
                for arg in set(d1.get(key, {}).get(nibble_id, {}).keys())
                | set(d2.get(key, {}).get(nibble_id, {}).keys())
            }
            for nibble_id in set(d1.get(key, {}).keys()) | set(d2.get(key, {}).keys())
        }
        for key in set(d1.keys()) | set(d2.keys())
    }


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
        self.cache: dict[OOI, dict[str, dict[tuple[Any, ...], set[OOI]]]] = {}
        self.update_nibbles()

    def __del__(self):
        self._write(datetime.now())

    def update_nibbles(self):
        self.nibbles: dict[str, NibbleDefinition] = get_nibble_definitions()

    def list_nibbles(self) -> list[str]:
        return list(self.nibbles.keys())

    def _run(self, ooi: OOI, valid_time: datetime) -> dict[str, dict[tuple[Any, ...], set[OOI]]]:
        return_value: dict[str, dict[tuple[Any, ...], set[OOI]]] = {}
        nibblets = self.origin_repository.list_origins(
            valid_time, origin_type=OriginType.NIBBLET, parameters_references=[ooi.reference]
        )
        for nibblet in nibblets:
            if nibblet.method in self.nibbles:
                nibble = self.nibbles[nibblet.method]
                args = self.ooi_repository.nibble_query(
                    ooi,
                    nibble,
                    valid_time,
                    nibblet.parameters_references if nibble.query is not None and nibble.query.count("$") > 0 else None,
                )
                results = {
                    tuple(arg): set(flatten([nibble(arg)]))
                    for arg in args
                    if nibblet.parameters_hash != nibble_hasher(arg)
                }
                return_value |= {nibble.id: results}
        nibblet_nibbles = {self.nibbles[nibblet.method] for nibblet in nibblets if nibblet.method in self.nibbles}
        for nibble in filter(lambda x: type(ooi) in x.signature and x not in nibblet_nibbles, self.nibbles.values()):
            if len(nibble.signature) > 1:
                self._write(valid_time)
            args = self.ooi_repository.nibble_query(ooi, nibble, valid_time)
            results = {tuple(arg): set(flatten([nibble(arg)])) for arg in args}
            return_value |= {nibble.id: results}
        self.cache = merge_results(self.cache, {ooi: return_value})
        return return_value

    def _write(self, valid_time: datetime):
        if self.perform_writes:
            for source_ooi, results in self.cache.items():
                self.ooi_repository.save(source_ooi, valid_time)
                for nibble_id, run_result in results.items():
                    for arg, result in run_result.items():
                        nibble_origin = Origin(
                            method=nibble_id,
                            origin_type=OriginType.NIBBLET,
                            source=source_ooi.reference,
                            result=[ooi.reference for ooi in result],
                            parameters_hash=nibble_hasher(arg),
                            parameters_references=[a.reference if isinstance(a, OOI) else None for a in arg],
                        )
                        for ooi in result:
                            self.ooi_repository.save(ooi, valid_time=valid_time)
                        self.origin_repository.save(nibble_origin, valid_time=valid_time)
            self.cache = {}

    def infer(self, stack: list[OOI], valid_time: datetime) -> dict[OOI, dict[str, dict[tuple[Any, ...], set[OOI]]]]:
        inferences: dict[OOI, dict[str, dict[tuple[Any, ...], set[OOI]]]] = {}
        blockset = set(stack)
        while stack:
            ooi = stack.pop()
            results = self._run(ooi, valid_time)
            if results:
                blocks = set.union(set(), *[ooiset for result in results.values() for _, ooiset in result.items()])
                stack += [o for o in blocks if o not in blockset]
                blockset |= blocks
                inferences |= {ooi: results}
        self._write(valid_time)
        return inferences

    def reset(self, valid_time: datetime) -> dict[OOI, dict[str, dict[tuple[Any, ...], set[OOI]]]]:
        nibblets = self.origin_repository.list_origins(valid_time, origin_type=OriginType.NIBBLET)
        refs = set(map(lambda nibblet: nibblet.source, nibblets))
        for nibblet in nibblets:
            # INFO: Probably we should adapt the event manager to cope with this
            # We are flooding the XTDB with events that will cause race conditions
            self.origin_repository.delete(nibblet, valid_time)
        return self.infer(self.ooi_repository.load_bulk_as_list(refs, valid_time), valid_time)
