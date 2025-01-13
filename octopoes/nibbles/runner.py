import json
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from xxhash import xxh3_128_hexdigest as xxh3

from nibbles.definitions import NibbleDefinition, get_nibble_definitions
from octopoes.models import OOI, Reference
from octopoes.models.origin import Origin, OriginType
from octopoes.repositories.nibble_repository import NibbleRepository
from octopoes.repositories.ooi_repository import OOIRepository
from octopoes.repositories.origin_repository import OriginRepository


def merge_results(
    d1: dict[OOI, dict[str, dict[tuple[Any, ...], set[OOI]]]], d2: dict[OOI, dict[str, dict[tuple[Any, ...], set[OOI]]]]
) -> dict[OOI, dict[str, dict[tuple[Any, ...], set[OOI]]]]:
    """
    Merge new runner results with old runner results
    d1: runner_results
    d2: runner_results
    --> runner_results
    """
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


def flatten(items: Iterable[Any | Iterable[Any | None] | None]) -> Iterable[OOI]:
    """
    Retrieve OOIs as returned from the nibble
    """
    for item in items:
        if isinstance(item, OOI):
            yield item
        elif item is None:
            continue
        elif isinstance(item, Iterable):
            yield from flatten(item)
        else:
            continue


def nibble_hasher(data: Iterable, additional: str | None = None) -> str:
    """
    Hash the nibble generated data with its content together with the nibble checksum
    """
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
        self, ooi_repository: OOIRepository, origin_repository: OriginRepository, nibble_repository: NibbleRepository
    ):
        self.ooi_repository = ooi_repository
        self.origin_repository = origin_repository
        self.cache: dict[OOI, dict[str, dict[tuple[Any, ...], set[OOI]]]] = {}
        self.nibble_repository = nibble_repository
        self.nibbles: dict[str, NibbleDefinition] = get_nibble_definitions()
        self.federated: bool = False

    def __del__(self):
        self._write(datetime.now())

    def update_nibbles(self, valid_time: datetime, new_nibbles: dict[str, NibbleDefinition] = get_nibble_definitions()):
        old_checksums = {nibble.id: nibble._checksum for nibble in self.nibbles.values()}
        self.nibbles = new_nibbles
        new_checksums = {nibble.id: nibble._checksum for nibble in self.nibbles.values()}
        if self.federated:
            self.register(valid_time)
        updated_nibble_ids = [
            nibble_id
            for nibble_id in new_checksums
            if nibble_id not in old_checksums or old_checksums[nibble_id] != new_checksums[nibble_id]
        ]
        self.infer(list(flatten(self.retrieve(updated_nibble_ids, valid_time).values())), valid_time)

    def list_nibbles(self) -> list[str]:
        return list(self.nibbles.keys())

    def list_available_nibbles(self) -> list[str]:
        return list(get_nibble_definitions())

    def disable(self):
        self.nibbles = {}

    def register(self, valid_time: datetime = datetime.now()):
        self.federated = True
        self.nibble_repository.put_many([nibble._ini for nibble in self.nibbles.values()], valid_time)

    def sync(self, valid_time: datetime):
        if self.federated:
            xtdb_nibble_inis = {ni["id"]: ni for ni in self.nibble_repository.get_all(valid_time)}
            for nibble in self.nibbles.values():
                xtdb_nibble_ini = xtdb_nibble_inis[nibble.id]
                if xtdb_nibble_ini["enabled"] != nibble.enabled:
                    self.nibbles[nibble.id].enabled = xtdb_nibble_ini["enabled"]

    def toggle_nibbles(self, nibble_ids: list[str], is_enabled: bool | list[bool], valid_time: datetime):
        is_enabled = is_enabled if isinstance(is_enabled, list) else [is_enabled] * len(nibble_ids)
        for nibble_id, state in zip(nibble_ids, is_enabled):
            self.nibbles[nibble_id].enabled = state
        if self.federated:
            self.nibble_repository.put_many([self.nibbles[nibble_id]._ini for nibble_id in nibble_ids], valid_time)

    def _retrieve(self, nibble_id: str, valid_time: datetime) -> list[list[Any]]:
        nibble = self.nibbles[nibble_id]
        if len(nibble.signature) > 1:
            return [list(args) for args in self.ooi_repository.nibble_query(None, nibble, valid_time)]
        else:
            t = nibble.signature[0].object_type
            if issubclass(t, OOI):
                return [[ooi] for ooi in self.ooi_repository.list_oois_by_object_types({t}, valid_time)]
            else:
                return [[]]

    def retrieve(self, nibble_ids: list[str] | None, valid_time: datetime) -> dict[str, list[list[Any]]]:
        return {
            nibble_id: self._retrieve(nibble_id, valid_time)
            for nibble_id in (nibble_ids if nibble_ids is not None else self.nibbles)
        }

    def yields(
        self, nibble_ids: list[str] | None, valid_time: datetime
    ) -> dict[str, dict[tuple[Reference | None, ...], list[Reference]]]:
        return {
            nibble_id: {
                tuple(nibblet.parameters_references): nibblet.result
                for nibblet in self.origin_repository.list_origins(
                    valid_time, origin_type=OriginType.NIBBLET, method=nibble_id
                )
                if nibblet.parameters_references is not None
            }
            for nibble_id in (nibble_ids if nibble_ids is not None else self.nibbles)
        }

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
            if nibble.enabled:
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
        self.sync(valid_time)
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
