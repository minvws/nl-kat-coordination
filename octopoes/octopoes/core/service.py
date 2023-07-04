import json
from collections import Counter
from datetime import datetime, timezone
from logging import getLogger
from typing import Callable, Dict, List, Optional, Set, Type

from bits.definitions import get_bit_definitions
from bits.runner import BitRunner

from octopoes.config.settings import (
    DEFAULT_LIMIT,
    DEFAULT_OFFSET,
    DEFAULT_SCAN_LEVEL_FILTER,
    DEFAULT_SCAN_PROFILE_TYPE_FILTER,
    Settings,
)
from octopoes.events.events import (
    DBEvent,
    OOIDBEvent,
    OriginDBEvent,
    OriginParameterDBEvent,
    ScanProfileDBEvent,
)
from octopoes.models import (
    OOI,
    DeclaredScanProfile,
    EmptyScanProfile,
    InheritedScanProfile,
    Reference,
    ScanLevel,
    ScanProfileType,
    format_id_short,
)
from octopoes.models.exception import ObjectNotFoundException
from octopoes.models.explanation import InheritanceSection
from octopoes.models.origin import Origin, OriginParameter, OriginType
from octopoes.models.pagination import Paginated
from octopoes.models.path import (
    Path,
    get_max_scan_level_inheritance,
    get_max_scan_level_issuance,
    get_paths_to_neighours,
)
from octopoes.models.tree import ReferenceTree
from octopoes.repositories.ooi_repository import OOIRepository
from octopoes.repositories.origin_parameter_repository import OriginParameterRepository
from octopoes.repositories.origin_repository import OriginRepository
from octopoes.repositories.scan_profile_repository import ScanProfileRepository

logger = getLogger(__name__)
settings = Settings()


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

    def _populate_scan_profiles(self, oois: List[OOI], valid_time: datetime) -> List[OOI]:
        logger.debug("Populating scan profiles for %s oois", len(oois))

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
        limit: int = DEFAULT_LIMIT,
        offset: int = DEFAULT_OFFSET,
        scan_levels: Set[ScanLevel] = DEFAULT_SCAN_LEVEL_FILTER,
        scan_profile_types: Set[ScanProfileType] = DEFAULT_SCAN_PROFILE_TYPE_FILTER,
    ) -> Paginated[OOI]:
        paginated = self.ooi_repository.list(types, valid_time, limit, offset, scan_levels, scan_profile_types)
        self._populate_scan_profiles(paginated.items, valid_time)
        return paginated

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

        # When an Origin is saved while the source OOI does not exist, reject saving the results
        if origin.origin_type != OriginType.DECLARATION and origin.source not in origin.result:
            try:
                self.ooi_repository.get(origin.source, valid_time)
            except ObjectNotFoundException:
                return

        for ooi in oois:
            self.ooi_repository.save(ooi, valid_time=valid_time)
        self.origin_repository.save(origin, valid_time=valid_time)

    def _run_inference(self, origin: Origin, valid_time: datetime) -> None:
        bit_definition = get_bit_definitions().get(origin.method, None)

        if bit_definition is None:
            self.save_origin(origin, [], valid_time)
            return

        is_disabled = bit_definition.id in settings.bits_disabled or (
            not bit_definition.default_enabled and bit_definition.id not in settings.bits_enabled
        )

        if is_disabled:
            self.save_origin(origin, [], valid_time)
            return

        try:
            level = self.scan_profile_repository.get(origin.source, valid_time).level
        except ObjectNotFoundException:
            level = 0

        if level < bit_definition.min_scan_level:
            self.save_origin(origin, [], valid_time)
            return

        source = self.ooi_repository.get(origin.source, valid_time)

        parameters_references = self.origin_parameter_repository.list_by_origin({origin.id}, valid_time)
        parameters = self.ooi_repository.load_bulk({x.reference for x in parameters_references}, valid_time)

        config = {}
        if bit_definition.config_ooi_relation_path is not None:
            configs = self.ooi_repository.get_bit_configs(source, bit_definition, valid_time)
            if len(configs) != 0:
                config = configs[-1].config

        try:
            resulting_oois = BitRunner(bit_definition).run(source, list(parameters.values()), config=config)
        except Exception as e:
            logger.exception("Error running inference", exc_info=e)
            return

        self.save_origin(origin, resulting_oois, valid_time)

    @staticmethod
    def check_path_level(path_level: Optional[int], current_level: int):
        return path_level is not None and path_level >= current_level

    def recalculate_scan_profiles(self, valid_time: datetime) -> None:
        # fetch all scan profiles
        all_scan_profiles = self.scan_profile_repository.list(None, valid_time=valid_time)

        # cache all declared
        all_declared_scan_profiles = {
            scan_profile for scan_profile in all_scan_profiles if isinstance(scan_profile, DeclaredScanProfile)
        }
        # cache all inherited
        inherited_scan_profiles = {
            scan_profile.reference: scan_profile
            for scan_profile in all_scan_profiles
            if isinstance(scan_profile, InheritedScanProfile)
        }

        # track all scan level assignments
        assigned_scan_levels: Dict[Reference, ScanLevel] = {
            scan_profile.reference: scan_profile.level for scan_profile in all_declared_scan_profiles
        }

        for current_level in range(4, 0, -1):
            # start point: all scan profiles with current level + all higher scan levels
            start_ooi_references = {
                profile.reference for profile in all_declared_scan_profiles if profile.level == current_level
            } | {reference for reference, level in assigned_scan_levels.items() if level > current_level}
            next_ooi_set = {ooi for ooi in self.ooi_repository.load_bulk(start_ooi_references, valid_time).values()}

            while next_ooi_set:
                # prepare next iteration, group oois per type
                ooi_types = {ooi.__class__ for ooi in next_ooi_set}
                grouped_per_type: Dict[Type[OOI], Set[OOI]] = {
                    ooi_type: {ooi for ooi in next_ooi_set if isinstance(ooi, ooi_type)} for ooi_type in ooi_types
                }

                temp_next_ooi_set = set()
                for ooi_type_ in grouped_per_type:
                    current_ooi_set = grouped_per_type[ooi_type_]

                    # find paths to neighbours higher or equal than current processing level
                    paths = get_paths_to_neighours(ooi_type_)
                    paths = {
                        path
                        for path in paths
                        if self.check_path_level(get_max_scan_level_issuance(path.segments[0]), current_level)
                    }

                    # If there are no paths at the current level we can go the next type
                    if not paths:
                        continue

                    # find all neighbours
                    references = {ooi.reference for ooi in current_ooi_set}
                    next_level = self.ooi_repository.list_neighbours(references, paths, valid_time)

                    # assign scan levels to newly found oois and add to next iteration
                    for ooi in next_level:
                        if ooi.reference not in assigned_scan_levels:
                            assigned_scan_levels[ooi.reference] = ScanLevel(current_level)
                            temp_next_ooi_set.add(ooi)

                logger.debug("Assigned scan levels [level=%i] [len=%i]", current_level, len(temp_next_ooi_set))
                next_ooi_set = temp_next_ooi_set

        scan_level_aggregates = {i: 0 for i in range(1, 5)}
        for scan_level in assigned_scan_levels.values():
            scan_level_aggregates.setdefault(scan_level.value, 0)
            scan_level_aggregates[scan_level] += 1

        logger.debug("Assigned scan levels [len=%i]", len(assigned_scan_levels.keys()))
        logger.debug(json.dumps(scan_level_aggregates, indent=4))

        # Save all assigned scan levels
        update_count = 0
        source_scan_profile_references = {sp.reference for sp in all_declared_scan_profiles}
        for reference, scan_level in assigned_scan_levels.items():
            # Skip source scan profiles
            if reference in source_scan_profile_references:
                continue

            new_scan_profile = InheritedScanProfile(reference=reference, level=scan_level)

            # Save new inherited scan profile
            if reference not in inherited_scan_profiles:
                self.scan_profile_repository.save(None, new_scan_profile, valid_time)
                update_count += 1
                continue

            # Diff with old scan profile
            old_scan_profile = inherited_scan_profiles[reference]
            if old_scan_profile.level != scan_level:
                self.scan_profile_repository.save(old_scan_profile, new_scan_profile, valid_time)
                update_count += 1

        logger.debug("Updated inherited scan profiles [count=%i]", update_count)

        # Reset previously assigned scan profiles to 0
        set_scan_profile_references = {
            scan_profile.reference for scan_profile in all_scan_profiles if scan_profile.level > 0
        }
        references_to_reset = (
            set_scan_profile_references - set(assigned_scan_levels.keys()) - source_scan_profile_references
        )
        for reference in references_to_reset:
            old_scan_profile = inherited_scan_profiles[reference]
            self.scan_profile_repository.save(old_scan_profile, EmptyScanProfile(reference=reference), valid_time)
        logger.debug("Reset scan profiles [len=%i]", len(references_to_reset))

        # Assign empty scan profiles to OOI's without scan profile
        unset_scan_profile_references = (
            self.ooi_repository.list_oois_without_scan_profile(valid_time)
            - set(assigned_scan_levels.keys())
            - source_scan_profile_references
            - references_to_reset
        )
        for reference in unset_scan_profile_references:
            self.scan_profile_repository.save(None, EmptyScanProfile(reference=reference), valid_time)
        logger.debug(
            "Assigned empty scan profiles to OOI's without scan profile [len=%i]", len(unset_scan_profile_references)
        )
        logger.info("Recalculated scan profiles")

    def process_event(self, event: DBEvent):
        # handle event
        event_handler_name = f"_on_{event.operation_type.value}_{event.entity_type}"
        handler: Optional[Callable[[DBEvent], None]] = getattr(self, event_handler_name)
        if handler is not None:
            handler(event)

        logger.debug(
            "Processed event [primary_key=%s] [operation_type=%s]",
            format_id_short(event.primary_key),
            event.operation_type,
        )

    # OOI events
    def _on_create_ooi(self, event: OOIDBEvent) -> None:
        ooi = event.new_data

        # keep old scan profile, or create new scan profile
        try:
            self.scan_profile_repository.get(ooi.reference, event.valid_time)
        except ObjectNotFoundException:
            self.scan_profile_repository.save(
                None,
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
                    try:
                        tree = self.ooi_repository.get_tree(
                            ooi.reference, valid_time=event.valid_time, depth=len(path_parts)
                        )
                    except ObjectNotFoundException:
                        # ooi is already removed, probably in parallel
                        return
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
        inference_origins = self.origin_repository.list_by_source(event.new_data.reference, valid_time=event.valid_time)
        inference_params = self.origin_parameter_repository.list_by_reference(
            event.new_data.reference, valid_time=event.valid_time
        )
        for inference_param in inference_params:
            inference_origins.append(self.origin_repository.get(inference_param.origin_id, event.valid_time))

        inference_origins = [o for o in inference_origins if o.origin_type == OriginType.INFERENCE]
        for inference_origin in inference_origins:
            self._run_inference(inference_origin, event.valid_time)

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

    def _run_inferences(self, event: ScanProfileDBEvent) -> None:
        inference_origins = self.origin_repository.list_by_source(event.reference, valid_time=event.valid_time)
        inference_origins = [o for o in inference_origins if o.origin_type == OriginType.INFERENCE]
        for inference_origin in inference_origins:
            self._run_inference(inference_origin, event.valid_time)

    # Scan profile events
    def _on_create_scan_profile(self, event: ScanProfileDBEvent) -> None:
        self._run_inferences(event)

    def _on_update_scan_profile(self, event: ScanProfileDBEvent) -> None:
        self._run_inferences(event)

    def _on_delete_scan_profile(self, event: ScanProfileDBEvent) -> None:
        self._run_inferences(event)

    def list_random_ooi(
        self, valid_time: datetime, amount: int = 1, scan_levels: Set[ScanLevel] = DEFAULT_SCAN_LEVEL_FILTER
    ) -> List[OOI]:
        oois = self.ooi_repository.list_random(valid_time, amount, scan_levels)
        self._populate_scan_profiles(oois, valid_time)
        return oois

    def get_scan_profile_inheritance(
        self, reference: Reference, valid_time: datetime, inheritance_chain: List[InheritanceSection]
    ) -> List[InheritanceSection]:
        neighbour_cache = self.ooi_repository.get_neighbours(reference, valid_time)

        last_inheritance_level = inheritance_chain[-1].level
        visited = {inheritance.reference for inheritance in inheritance_chain}

        # load scan profiles for all neighbours
        neighbours_: List[OOI] = [
            neighbour
            for neighbours in neighbour_cache.values()
            for neighbour in neighbours
            if neighbour.reference not in visited
        ]
        self._populate_scan_profiles(neighbours_, valid_time)

        # collect all inheritances
        inheritances = []
        for path, neighbours in neighbour_cache.items():
            segment = path.segments[0]
            for neighbour in neighbours:
                segment_inheritance = get_max_scan_level_inheritance(segment)
                if (
                    segment_inheritance is None
                    or neighbour.reference in visited
                    or neighbour.scan_profile.level < last_inheritance_level
                ):
                    continue

                inherited_level = min(get_max_scan_level_inheritance(segment), neighbour.scan_profile.level)
                inheritances.append(
                    InheritanceSection(
                        segment=str(segment),
                        reference=neighbour.reference,
                        level=inherited_level,
                        scan_profile_type=neighbour.scan_profile.scan_profile_type,
                    )
                )

        # sort per ooi, per level, ascending
        inheritances.sort(key=lambda x: x.level)

        # if any declared, return highest straight away
        declared_inheritances = [
            inheritance for inheritance in inheritances if inheritance.scan_profile_type == ScanProfileType.DECLARED
        ]
        if declared_inheritances:
            return inheritance_chain + [declared_inheritances[-1]]

        # group by ooi, as the list is already sorted, it will contain the highest inheritance
        highest_inheritance_per_neighbour = {
            inheritance.reference: inheritance for inheritance in reversed(inheritances)
        }

        # traverse depth-first, highest levels first
        for inheritance in sorted(highest_inheritance_per_neighbour.values(), key=lambda x: x.level, reverse=True):
            expl = self.get_scan_profile_inheritance(
                inheritance.reference, valid_time, inheritance_chain + [inheritance]
            )
            if expl[-1].scan_profile_type == ScanProfileType.DECLARED:
                return expl

        return inheritance_chain

    def recalculate_bits(self) -> int:
        valid_time = datetime.now(timezone.utc)
        bit_counter = Counter()

        # loop over all bit definitions and add origins and origin params
        bit_definitions = get_bit_definitions()
        for bit_id, bit_definition in bit_definitions.items():
            # loop over all oois that are consumed by the bit
            for ooi in self.ooi_repository.list({bit_definition.consumes}, limit=20000, valid_time=valid_time).items:
                if not isinstance(ooi, bit_definition.consumes):
                    logger.exception("Wut?")

                # insert, if not exists
                bit_instance = Origin(
                    origin_type=OriginType.INFERENCE,
                    method=bit_id,
                    source=ooi.reference,
                )
                try:
                    self.origin_repository.get(bit_instance.id, valid_time)
                except ObjectNotFoundException:
                    self.origin_repository.save(bit_instance, valid_time)
                    bit_counter.update({bit_instance.method})

                for param_def in bit_definition.parameters:
                    path = Path.parse(f"{param_def.ooi_type.get_object_type()}.{param_def.relation_path}").reverse()

                    param_oois = self.ooi_repository.list_related(ooi, path, valid_time=valid_time)
                    for param_ooi in param_oois:
                        param = OriginParameter(origin_id=bit_instance.id, reference=param_ooi.reference)
                        self.origin_parameter_repository.save(param, valid_time)

        # TODO: remove all Origins and Origin Parameters, which are no longer in use

        # rerun all existing bits
        origins = self.origin_repository.list(origin_type=OriginType.INFERENCE, valid_time=valid_time)
        for origin in origins:
            self._run_inference(origin, valid_time)
            bit_counter.update({origin.method})

        return sum(bit_counter.values())
