import json
import uuid
from datetime import datetime
from logging import getLogger
from typing import List, Optional, Callable, Set, Dict, Type

from bits.definitions import get_bit_definitions
from bits.runner import BitRunner
from octopoes.events.events import (
    OOIDBEvent,
    OriginDBEvent,
    OriginParameterDBEvent,
    ScanProfileDBEvent,
    DBEvent,
    CalculateScanLevelTask,
)
from octopoes.models import (
    OOI,
    Reference,
    ScanProfileBase,
    InheritedScanProfile,
    DeclaredScanProfile,
    Inheritance,
    EmptyScanProfile,
)
from octopoes.models.exception import ObjectNotFoundException
from octopoes.models.origin import Origin, OriginType, OriginParameter
from octopoes.models.path import get_max_scan_level_inheritance, get_max_scan_level_issuance, Path
from octopoes.models.tree import ReferenceTree
from octopoes.repositories.ooi_repository import OOIRepository
from octopoes.repositories.origin_parameter_repository import OriginParameterRepository
from octopoes.repositories.origin_repository import OriginRepository
from octopoes.repositories.scan_profile_repository import ScanProfileRepository
from octopoes.tasks.app import app as celery_app

logger = getLogger(__name__)


def find_relation_in_tree(relation: str, tree: ReferenceTree) -> List[OOI]:
    parts = relation.split(".")
    nodes = [tree.root]
    for part in parts:
        child_nodes = []
        for node in nodes:
            if part in node.children:
                child_nodes.extend(node.children[part])
        nodes = child_nodes
    return [tree.store[str(node.reference)] for node in nodes]


class OctopoesService:
    def __init__(
        self,
        ooi_repository: OOIRepository,
        origin_repository: OriginRepository,
        origin_parameter_repository: OriginParameterRepository,
        scan_profile_repository: ScanProfileRepository,
    ):
        self.ooi_repository = ooi_repository
        self.origin_repository = origin_repository
        self.origin_parameter_repository = origin_parameter_repository
        self.scan_profile_repository = scan_profile_repository

    def _dispatch_calculate_scan_profile(self, reference: Reference, client: str, valid_time: datetime) -> None:
        task = CalculateScanLevelTask(
            reference=reference,
            valid_time=valid_time,
            client=client,
        )

        logger.info("Dispatching CalculateScanLevelTask event: %s", task.json())

        celery_app.send_task(
            "octopoes.tasks.tasks.calculate_scan_profile",
            (json.loads(task.json()),),
            queue="octopoes",
            task_id=str(uuid.uuid4()),
        )

    def _populate_scan_profiles(self, oois: List[OOI], valid_time: datetime) -> List[OOI]:
        logger.info("Populating scan profiles for %s oois", len(oois))

        ooi_cache: Dict[str, OOI] = {str(ooi.reference): ooi for ooi in oois}
        scan_profiles = self.scan_profile_repository.get_bulk({x.reference for x in oois}, valid_time)
        for ooi in oois:
            ooi.scan_profile = EmptyScanProfile(reference=ooi.reference)
        for scan_profile in scan_profiles:
            ooi_cache[str(scan_profile.reference)].scan_profile = scan_profile

        return oois

    def get_ooi(self, reference: Reference, valid_time: datetime) -> OOI:
        ooi = self.ooi_repository.get(reference, valid_time)
        return self._populate_scan_profiles([ooi], valid_time)[0]

    def list_ooi(
        self,
        types: Set[Type[OOI]],
        valid_time: datetime,
        limit: int = 1000,
        offset: int = 0,
    ) -> List[OOI]:
        return self._populate_scan_profiles(self.ooi_repository.list(types, valid_time, limit, offset), valid_time)

    def get_ooi_tree(
        self,
        reference: Reference,
        valid_time: datetime,
        search_types: Optional[Set[Type[OOI]]] = None,
        depth: Optional[int] = 1,
    ):
        tree = self.ooi_repository.get_tree(reference, valid_time, search_types, depth)
        self._populate_scan_profiles(tree.store.values(), valid_time)
        return tree

    def _delete_ooi(self, reference: Reference, valid_time: datetime) -> None:
        referencing_origins = self.origin_repository.list_by_result(reference, valid_time)
        if not referencing_origins:
            self.ooi_repository.delete(reference, valid_time)

    def save_origin(self, origin: Origin, oois: List[OOI], valid_time: datetime) -> None:

        origin.result = [ooi.reference for ooi in oois]

        if origin.origin_type != OriginType.DECLARATION and origin.source not in origin.result:
            try:
                self.ooi_repository.get(origin.source, valid_time)
            except ObjectNotFoundException:
                return

        for ooi in oois:
            self.ooi_repository.save(ooi, valid_time=valid_time)
        self.origin_repository.save(origin, valid_time=valid_time)

    def _run_inference(self, origin: Origin, valid_time: datetime):

        bit_definition = get_bit_definitions()[origin.method]

        source = self.ooi_repository.get(origin.source, valid_time)

        parameters_references = self.origin_parameter_repository.list_by_origin(origin.id, valid_time)
        parameters = self.ooi_repository.get_bulk({x.reference for x in parameters_references}, valid_time)

        resulting_oois = BitRunner(bit_definition).run(source, list(parameters.values()))
        self.save_origin(origin, resulting_oois, valid_time)

    @staticmethod
    def _calculate_inheritances_from_neighbours(
        ooi: OOI, grouped_neighbours: Dict[Path, List[OOI]], source_scan_levels: Dict[Reference, DeclaredScanProfile]
    ) -> Dict[str, Inheritance]:

        all_inheritances: List[Inheritance] = []

        for path, neighbours in grouped_neighbours.items():
            relation_max_inheritance = get_max_scan_level_inheritance(path.segments[0])

            # undefined inheritance, means no inheritance
            if relation_max_inheritance is None:
                continue

            for neighbour in neighbours:

                # can't inherit from self
                if neighbour.reference == ooi.reference:
                    continue

                # neighbour is empty, don't inherit
                if isinstance(neighbour.scan_profile, EmptyScanProfile):
                    continue

                max_relation_inheritance_level = min(relation_max_inheritance, neighbour.scan_profile.level)

                # neighbour is declared, direct inheritance
                if isinstance(neighbour.scan_profile, DeclaredScanProfile):
                    all_inheritances.append(
                        Inheritance(
                            source=neighbour.reference,
                            parent=neighbour.reference,
                            level=max_relation_inheritance_level,
                            depth=1,
                        )
                    )
                    continue

                # neighbour is inheriting, calculate inheritance
                if isinstance(neighbour.scan_profile, InheritedScanProfile):

                    for neighbouring_inheritance in neighbour.scan_profile.inheritances:

                        if neighbouring_inheritance.parent == ooi.reference:
                            continue

                        # when the source level is not found, don't inherit
                        if neighbouring_inheritance.source not in source_scan_levels:
                            logger.warning("Inheritance source not found: %s", neighbouring_inheritance.source)
                            continue

                        actual_source_level = source_scan_levels[neighbouring_inheritance.source]

                        # inherit neighbour inheritance, but not higher than source, and now higher than max relation level
                        actual_inheriting_level = min(
                            max_relation_inheritance_level,
                            actual_source_level.level,
                            neighbouring_inheritance.level,
                        )

                        all_inheritances.append(
                            Inheritance(
                                source=neighbouring_inheritance.source,
                                parent=neighbour.reference,
                                level=actual_inheriting_level,
                                depth=neighbouring_inheritance.depth + 1,
                            )
                        )

        # group inheritances per source
        inheritances_per_source: Dict[Reference, List[Inheritance]] = {}
        for inheritance in all_inheritances:
            inheritances_per_source.setdefault(inheritance.source, []).append(inheritance)

        result_inheritances: Dict[str, Inheritance] = {}
        for source, inheritances in inheritances_per_source.items():

            # always pick declared over inherited
            declared = [inheritance for inheritance in inheritances if inheritance.parent == inheritance.source]
            if declared:
                result_inheritances[str(source)] = next(iter(declared))
                continue

            # filter by highest level
            highest_level = max([x.level for x in inheritances])
            filtered_inheritances = [inheritance for inheritance in inheritances if inheritance.level == highest_level]

            # filter by lowest depth
            lowest_depth = min([x.depth for x in filtered_inheritances])
            filtered_inheritances = [
                inheritance for inheritance in filtered_inheritances if inheritance.depth == lowest_depth
            ]

            # sort by parent to make sure the order is consistent in the case of draws
            filtered_inheritances = sorted(filtered_inheritances, key=lambda x: str(x.parent))

            # add first to result
            result_inheritances[str(source)] = next(iter(filtered_inheritances))

        return result_inheritances

    def _calculate_scan_profile(self, ooi: OOI, current_scan_profile: ScanProfileBase, valid_time: datetime):

        if isinstance(current_scan_profile, DeclaredScanProfile):
            return

        if ooi.primary_key == "DNSZone|internet|minvws.nl.":
            print(ooi.primary_key)

        neighbours_by_path = self.ooi_repository.get_neighbours(ooi.reference, valid_time)

        # flatten oois and load scan profiles
        neighbouring_oois = [ooi for neighbours in neighbours_by_path.values() for ooi in neighbours]
        self._populate_scan_profiles(neighbouring_oois, valid_time)

        # get sources to execute equation

        # extract from neighbours
        sources: Dict[Reference, DeclaredScanProfile] = {}
        for path, neighbours in neighbours_by_path.items():
            for neighbour in neighbours:
                if isinstance(neighbour.scan_profile, DeclaredScanProfile):
                    sources[neighbour.reference] = neighbour.scan_profile

        # query remaining sources
        for path, neighbours in neighbours_by_path.items():
            for neighbour in neighbours:
                if isinstance(neighbour.scan_profile, InheritedScanProfile):
                    for inheritance in neighbour.scan_profile.inheritances:
                        if inheritance.source not in sources:
                            try:
                                source = self.scan_profile_repository.get(inheritance.source, valid_time)
                                if isinstance(source, DeclaredScanProfile):
                                    sources[source.reference] = source
                            except ObjectNotFoundException:
                                pass
        # calculate inheritance
        inheritances = self._calculate_inheritances_from_neighbours(ooi, neighbours_by_path, sources)

        # determine new scan profile
        if not inheritances:
            new_scan_profile = EmptyScanProfile(reference=ooi.reference)
        else:
            new_scan_profile = InheritedScanProfile(
                reference=ooi.reference,
                level=max([inheritance.level for inheritance in inheritances.values()]),
                inheritances=list(inheritances.values()),
            )

        self.scan_profile_repository.save(new_scan_profile, valid_time=valid_time)

    def process_event(self, event: DBEvent):
        logger.info("Received event: %s", event.json())

        # handle event
        event_handler_name = f"_on_{event.operation_type.value}_{event.entity_type}"
        handler: Optional[Callable[[DBEvent], None]] = getattr(self, event_handler_name)
        if handler is not None:
            logger.info("Processing event with handler '%s'", event_handler_name)

            handler(event)

    # OOI events
    def _on_create_ooi(self, event: OOIDBEvent) -> None:
        ooi = event.new_data

        # keep old scan profile, or create new scan profile
        try:
            self.scan_profile_repository.get(ooi.reference, event.valid_time)
        except ObjectNotFoundException:
            self.scan_profile_repository.save(
                EmptyScanProfile(reference=ooi.reference),
                valid_time=event.valid_time,
            )

        # analyze bit definitions
        bit_definitions = get_bit_definitions()
        for bit_id, bit_definition in bit_definitions.items():

            # attach bit instances
            if isinstance(ooi, bit_definition.consumes):

                bit_instance = Origin(
                    origin_type=OriginType.INFERENCE,
                    method=bit_id,
                    source=ooi.reference,
                )
                self.origin_repository.save(bit_instance, event.valid_time)

            # attach bit parameters
            for additional_param in bit_definition.parameters:
                if isinstance(ooi, additional_param.ooi_type):

                    path_parts = additional_param.relation_path.split(".")
                    tree = self.ooi_repository.get_tree(
                        ooi.reference, valid_time=event.valid_time, depth=len(path_parts)
                    )
                    bit_ancestor = find_relation_in_tree(additional_param.relation_path, tree)

                    if bit_ancestor:
                        origin = Origin(
                            origin_type=OriginType.INFERENCE,
                            method=bit_id,
                            source=bit_ancestor[0].reference,
                        )
                        origin_parameter = OriginParameter(
                            origin_id=origin.id,
                            reference=ooi.reference,
                        )
                        self.origin_parameter_repository.save(origin_parameter, event.valid_time)

    def _on_update_ooi(self, event: OOIDBEvent) -> None:
        ...

    def _on_delete_ooi(self, event: OOIDBEvent) -> None:

        reference = event.old_data.reference

        # delete related origins to which it is a source
        origins = self.origin_repository.list_by_source(reference, event.valid_time)
        for origin in origins:
            self.origin_repository.delete(origin, event.valid_time)

        # delete related origin parameters
        origin_parameters = self.origin_parameter_repository.list_by_reference(reference, event.valid_time)
        for origin_parameter in origin_parameters:
            self.origin_parameter_repository.delete(origin_parameter, event.valid_time)

        # delete scan profile
        try:
            scan_profile = self.scan_profile_repository.get(reference, event.valid_time)
            self.scan_profile_repository.delete(scan_profile, event.valid_time)
        except ObjectNotFoundException:
            pass

    # Origin events
    def _on_create_origin(self, event: OriginDBEvent) -> None:
        if event.new_data.origin_type == OriginType.INFERENCE:
            self._run_inference(event.new_data, event.valid_time)

    def _on_update_origin(self, event: OriginDBEvent) -> None:
        dereferenced_oois = event.old_data - event.new_data
        for reference in dereferenced_oois:
            self._delete_ooi(reference, event.valid_time)

    def _on_delete_origin(self, event: OriginDBEvent) -> None:
        for reference in event.old_data.result:
            self._delete_ooi(reference, event.valid_time)

    # Origin parameter events
    def _on_create_origin_parameter(self, event: OriginParameterDBEvent) -> None:
        # Run the bit/origin
        try:
            origin = self.origin_repository.get(event.new_data.origin_id, event.valid_time)
            self._run_inference(origin, event.valid_time)
        except ObjectNotFoundException:
            return

    def _on_update_origin_parameter(self, event: OriginParameterDBEvent) -> None:
        # update of origin_parameter is not possible, since both fields are unique
        ...

    def _on_delete_origin_parameter(self, event: OriginParameterDBEvent) -> None:
        # Run the bit/origin
        try:
            origin = self.origin_repository.get(event.old_data.origin_id, event.valid_time)
            self._run_inference(origin, event.valid_time)
        except ObjectNotFoundException:
            return

    # Scan profile events
    def _on_create_scan_profile(self, event: ScanProfileDBEvent) -> None:
        self._dispatch_calculate_scan_profile(event.new_data.reference, event.client, event.valid_time)

    def _on_update_scan_profile(self, event: ScanProfileDBEvent) -> None:
        try:
            ooi = self.ooi_repository.get(event.new_data.reference, event.valid_time)
            neighbours_by_path = self.ooi_repository.get_neighbours(ooi.reference, event.valid_time)

            # load scan profiles efficiently
            neighbouring_oois = [ooi for neighbours in neighbours_by_path.values() for ooi in neighbours]
            self._populate_scan_profiles(neighbouring_oois, event.valid_time)

            # recalculate scan profile for affected neighbours
            for path, neighbours in neighbours_by_path.items():

                relation_max_issuance = get_max_scan_level_issuance(path.segments[0])

                # undefined inheritance, means no inheritance
                if relation_max_issuance is None:
                    continue

                for neighbour in neighbours:

                    # don't follow self-references
                    if neighbour.reference == ooi.reference:
                        continue

                    self._dispatch_calculate_scan_profile(neighbour.reference, event.client, event.valid_time)

        except ObjectNotFoundException:
            return None

    def _on_delete_scan_profile(self, event: ScanProfileDBEvent) -> None:
        old_ooi_reference = event.old_data.reference
        child_scan_levels = self.scan_profile_repository.list_by_parent(old_ooi_reference, event.valid_time)
        for child in child_scan_levels:
            self._dispatch_calculate_scan_profile(child.reference, event.client, event.valid_time)

    def list_random_ooi(self, amount: int, valid_time: datetime) -> List[OOI]:
        oois = self.ooi_repository.list_random(amount, valid_time)
        self._populate_scan_profiles(oois, valid_time)
        return oois
