import json
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from xxhash import xxh3_128_hexdigest as xxh3  # INFO: xxh3_64_hexdigest is faster but hash more collision probabilities

from nibbles.definitions import NibbleDefinition, get_nibble_definitions
from octopoes.models import OOI, Reference
from octopoes.models.origin import Origin, OriginType
from octopoes.repositories.ooi_repository import OOIRepository
from octopoes.repositories.origin_repository import OriginRepository
from octopoes.repositories.scan_profile_repository import ScanProfileRepository


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


def nibble_hasher(data: Iterable, additional: str | None = None) -> str:
    return xxh3(
        "".join(
            [
                json.dumps(json.loads(ooi.model_dump_json()), sort_keys=True)
                if isinstance(ooi, OOI)
                else json.dumps(ooi, sort_keys=True)
                for ooi in data
            ]
        )
        + (additional or "")
    )


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
        self.cache: dict[OOI, dict[str, dict[tuple[Any, ...], set[OOI]]]] = {}
        self.nibbles: dict[str, NibbleDefinition] = get_nibble_definitions()

    def __del__(self):
        self._write(datetime.now())

    def update_nibbles(self, valid_time: datetime):
        self.nibbles = get_nibble_definitions()
        # FIXME: this is nice, but does not allow newly affected elements -- this will be addressed shortly
        nibblets = self.origin_repository.list_origins(valid_time, origin_type=OriginType.NIBBLET)
        refs = set(map(lambda nibblet: nibblet.source, nibblets))
        self.infer(self.ooi_repository.load_bulk_as_list(refs, valid_time), valid_time)

    def select_nibbles(self, nibble_ids: Iterable[str]):
        self.nibbles = {key: value for key, value in self.nibbles.items() if key in nibble_ids}

    def list_nibbles(self) -> list[str]:
        return list(self.nibbles.keys())

    def list_available_nibbles(self) -> list[str]:
        return list(get_nibble_definitions())

    def checksum_nibbles(self) -> dict[str, str | None]:
        return {nibble.id: nibble._checksum for nibble in self.nibbles.values()}

    def disable(self):
        self.nibbles = {}

    def retrieve(self, nibble_id: str, valid_time: datetime) -> list[list[Any]]:
        nibble = self.nibbles[nibble_id]
        if len(nibble.signature) > 1:
            return [list(args) for args in self.ooi_repository.nibble_query(None, nibble, valid_time)]
        else:
            t = nibble.signature[0].object_type
            if issubclass(t, OOI):
                return [[ooi] for ooi in self.ooi_repository.list_oois_by_object_types({t}, valid_time)]
            else:
                return [[]]

    def retrieve_all(self, valid_time: datetime) -> dict[str, list[list[Any]]]:
        return {nibble_id: self.retrieve(nibble_id, valid_time) for nibble_id in self.nibbles}

    def yields(self, nibble_id: str, valid_time: datetime) -> dict[tuple[Reference | None, ...], list[Reference]]:
        return {
            tuple(nibblet.parameters_references): nibblet.result
            for nibblet in self.origin_repository.list_origins(
                valid_time, origin_type=OriginType.NIBBLET, method=nibble_id
            )
            if nibblet.parameters_references is not None
        }

    def yields_all(self, valid_time: datetime) -> dict[str, dict[tuple[Reference | None, ...], list[Reference]]]:
        return {nibble_id: self.yields(nibble_id, valid_time) for nibble_id in self.nibbles}

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
                    nibblet.parameters_references
                    if nibble.query is not None and (callable(nibble.query) or isinstance(nibble.query, str))
                    else None,
                )
                results = {
                    tuple(arg): set(flatten([nibble(arg)]))
                    for arg in args
                    if nibblet.parameters_hash != nibble_hasher(arg, nibble._checksum)
                }
                return_value |= {nibble.id: results}
        nibblet_nibbles = {self.nibbles[nibblet.method] for nibblet in nibblets if nibblet.method in self.nibbles}

        for nibble in filter(
            lambda x: any(isinstance(ooi, param.object_type) for param in x.signature) and x not in nibblet_nibbles,
            self.nibbles.values(),
        ):
            if len(nibble.signature) > 1:
                self._write(valid_time)
            args = self.ooi_repository.nibble_query(ooi, nibble, valid_time)
            results = {tuple(arg): set(flatten([nibble(arg)])) for arg in args}
            return_value |= {nibble.id: results}
        self.cache = merge_results(self.cache, {ooi: return_value})
        return return_value

    def _write(self, valid_time: datetime):
        for source_ooi, results in self.cache.items():
            self.ooi_repository.save(source_ooi, valid_time)
            for nibble_id, run_result in results.items():
                for arg, result in run_result.items():
                    nibble_origin = Origin(
                        method=nibble_id,
                        origin_type=OriginType.NIBBLET,
                        source=source_ooi.reference,
                        result=[ooi.reference for ooi in result],
                        parameters_hash=nibble_hasher(arg, self.nibbles[nibble_id]._checksum),
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
