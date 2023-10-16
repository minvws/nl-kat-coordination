from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import datetime
from http import HTTPStatus
from typing import Any, Dict, List, Optional, Set, Tuple, Type, Union, cast

from bits.definitions import BitDefinition
from pydantic import BaseModel, parse_obj_as
from requests import HTTPError

from octopoes.config.settings import (
    DEFAULT_LIMIT,
    DEFAULT_OFFSET,
    DEFAULT_SCAN_LEVEL_FILTER,
    DEFAULT_SCAN_PROFILE_TYPE_FILTER,
    XTDBType,
)
from octopoes.events.events import OOIDBEvent, OperationType
from octopoes.events.manager import EventManager
from octopoes.models import (
    OOI,
    Reference,
    ScanLevel,
    ScanProfileType,
)
from octopoes.models.exception import ObjectNotFoundException
from octopoes.models.ooi.config import Config
from octopoes.models.ooi.findings import Finding, FindingType, RiskLevelSeverity
from octopoes.models.pagination import Paginated
from octopoes.models.path import Direction, Path, Segment, get_paths_to_neighours
from octopoes.models.tree import ReferenceNode, ReferenceTree
from octopoes.models.types import get_concrete_types, get_relation, get_relations, to_concrete, type_by_name
from octopoes.repositories.repository import Repository
from octopoes.xtdb import Datamodel, FieldSet, ForeignKey
from octopoes.xtdb.client import OperationType as XTDBOperationType
from octopoes.xtdb.client import XTDBSession
from octopoes.xtdb.query import Query
from octopoes.xtdb.query_builder import generate_pull_query, str_val
from octopoes.xtdb.related_field_generator import RelatedFieldNode

logger = logging.getLogger(__name__)


def merge_ooi(ooi_new: OOI, ooi_old: OOI) -> Tuple[OOI, bool]:
    data_old = ooi_old.dict()
    data_new = ooi_new.dict()

    # Trim new None values
    clean_new = {key: val for key, val in data_new.items() if val is not None}

    changed = False
    for key, value in clean_new.items():
        if key in data_old and data_old[key] != value:
            changed = True
            break

    data_old.update(clean_new)
    return ooi_new.__class__.parse_obj(data_old), changed


class OOIRepository(Repository):
    def __init__(self, event_manager: EventManager):
        self.event_manager = event_manager

    def get(self, reference: Reference, valid_time: datetime) -> OOI:
        raise NotImplementedError

    def load_bulk(self, references: Set[Reference], valid_time: datetime) -> Dict[str, OOI]:
        raise NotImplementedError

    def get_neighbours(
        self, reference: Reference, valid_time: datetime, paths: Optional[Set[Path]] = None
    ) -> Dict[Path, List[OOI]]:
        raise NotImplementedError

    def list(
        self,
        types: Set[Type[OOI]],
        valid_time: datetime,
        offset: int = 0,
        limit: int = 20,
        scan_levels: Set[ScanLevel] = DEFAULT_SCAN_LEVEL_FILTER,
        scan_profile_types: Set[ScanProfileType] = DEFAULT_SCAN_PROFILE_TYPE_FILTER,
    ) -> Paginated[OOI]:
        raise NotImplementedError

    def list_random(
        self, valid_time: datetime, amount: int = 1, scan_levels: Set[ScanLevel] = DEFAULT_SCAN_LEVEL_FILTER
    ) -> List[OOI]:
        raise NotImplementedError

    def list_neighbours(self, references: Set[Reference], paths: Set[Path], valid_time: datetime) -> Set[OOI]:
        raise NotImplementedError

    def save(self, ooi: OOI, valid_time: datetime, end_valid_time: Optional[datetime] = None) -> None:
        raise NotImplementedError

    def delete(self, reference: Reference, valid_time: datetime) -> None:
        raise NotImplementedError

    def get_tree(
        self,
        reference: Reference,
        valid_time: datetime,
        search_types: Optional[Set[Type[OOI]]] = None,
        depth: Optional[int] = 1,
    ) -> ReferenceTree:
        raise NotImplementedError

    def list_oois_without_scan_profile(self, valid_time: datetime) -> Set[Reference]:
        raise NotImplementedError

    def count_findings_by_severity(self, valid_time: datetime) -> Counter:
        raise NotImplementedError

    def list_findings(
        self,
        severities,
        exclude_muted,
        offset,
        limit,
        valid_time,
    ) -> Paginated[Finding]:
        raise NotImplementedError

    def get_bit_configs(self, source: OOI, bit_definition: BitDefinition, valid_time: datetime) -> List[Config]:
        raise NotImplementedError

    def list_related(self, ooi: OOI, path: Path, valid_time: datetime) -> List[OOI]:
        raise NotImplementedError

    def query(self, query: Query, valid_time: datetime) -> List[OOI]:
        raise NotImplementedError


class XTDBReferenceNode(BaseModel):
    __root__: Dict[str, Union[str, List[XTDBReferenceNode], XTDBReferenceNode]]

    def to_reference_node(self, pk_prefix: str) -> Optional[ReferenceNode]:
        if not self.__root__:
            return None
        # Apparently relations can be joined to Null values..?!?
        if pk_prefix not in self.__root__:
            return None
        reference = Reference.from_str(self.__root__.pop(pk_prefix))
        children = {}
        for name, value in self.__root__.items():
            if isinstance(value, XTDBReferenceNode):
                sub_nodes = [value.to_reference_node(pk_prefix)]
            elif isinstance(value, (List, Set)):
                sub_nodes = [val_.to_reference_node(pk_prefix) for val_ in value]
            sub_nodes = [node for node in sub_nodes if node is not None]
            if sub_nodes:
                children[name] = sub_nodes
        return ReferenceNode(reference=reference, children=children)


XTDBReferenceNode.update_forward_refs()

entities = {}
for ooi_type_ in get_concrete_types():
    fks = []
    for field_name, related in get_relations(ooi_type_).items():
        related_entities = {r.__name__ for r in to_concrete({related})}
        fks.append(
            ForeignKey(
                source_entity=ooi_type_.get_object_type(),
                attr_name=field_name,
                related_entities=related_entities,
                reverse_name=ooi_type_.get_reverse_relation_name(field_name),
            )
        )
    entities[ooi_type_.get_object_type()] = fks

datamodel = Datamodel(entities=entities)


class XTDBOOIRepository(OOIRepository):
    xtdb_type: XTDBType = XTDBType.CRUX

    def __init__(self, event_manager: EventManager, session: XTDBSession, xtdb_type: XTDBType):
        super().__init__(event_manager)
        self.session = session
        self.__class__.xtdb_type = xtdb_type

    def commit(self):
        self.session.commit()

    @classmethod
    def pk_prefix(cls):
        return "crux.db/id" if cls.xtdb_type == XTDBType.CRUX else "xt/id"

    @classmethod
    def serialize(cls, ooi: OOI) -> Dict[str, Any]:
        # export model with pydantic serializers
        export = json.loads(ooi.json())

        # prefix fields, but not object_type
        export.pop("object_type")
        export = {f"{ooi.__class__.__name__}/{key}": value for key, value in export.items() if value is not None}

        export["object_type"] = ooi.__class__.__name__
        export[cls.pk_prefix()] = ooi.primary_key

        return export

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> OOI:
        if "object_type" not in data:
            raise ValueError

        # pop global attributes
        object_cls = type_by_name(data.pop("object_type"))
        data.pop(cls.pk_prefix())

        # remove type prefixes
        stripped = {key.split("/")[1]: value for key, value in data.items()}
        return object_cls.parse_obj(stripped)

    def get(self, reference: Reference, valid_time: datetime) -> OOI:
        try:
            res = self.session.client.get_entity(str(reference), valid_time)
            return self.deserialize(res)
        except HTTPError as e:
            if e.response.status_code == HTTPStatus.NOT_FOUND:
                raise ObjectNotFoundException(str(reference))

    def load_bulk(self, references: Set[Reference], valid_time: datetime) -> Dict[str, OOI]:
        ids = list(map(str, references))
        query = generate_pull_query(self.xtdb_type, FieldSet.ALL_FIELDS, {self.pk_prefix(): ids})
        res = self.session.client.query(query, valid_time)
        oois = [self.deserialize(x[0]) for x in res]
        return {ooi.primary_key: ooi for ooi in oois}

    def list(
        self,
        types: Set[Type[OOI]],
        valid_time: datetime,
        offset: int = 0,
        limit: int = 20,
        scan_levels: Set[ScanLevel] = DEFAULT_SCAN_LEVEL_FILTER,
        scan_profile_types: Set[ScanProfileType] = DEFAULT_SCAN_PROFILE_TYPE_FILTER,
    ) -> Paginated[OOI]:
        types = to_concrete(types)

        count_query = """
                {{
                    :query {{
                        :find [(count ?e)]
                        :in [[_object_type ...] [_scan_level ...] [_scan_profile_type ...]]
                        :where [[?e :object_type _object_type]
                                [?scan_profile :type "ScanProfile"]
                                [?scan_profile :reference ?e]
                                [?scan_profile :level _scan_level]
                                [?scan_profile :scan_profile_type _scan_profile_type]]
                    }}
                    :in-args [[{object_types}], [{scan_levels}], [{scan_profile_types}]]
                }}
                """.format(
            object_types=" ".join(map(lambda t: str_val(t.get_object_type()), types)),
            scan_levels=" ".join([str(scan_level.value) for scan_level in scan_levels]),
            scan_profile_types=" ".join([str_val(scan_profile_type.value) for scan_profile_type in scan_profile_types]),
        )

        res_count = self.session.client.query(count_query, valid_time)
        count = res_count[0][0] if res_count else 0

        data_query = """
                {{
                    :query {{
                        :find [(pull ?e [*])]
                        :in [[_object_type ...] [_scan_level ...]  [_scan_profile_type ...]]
                        :where [[?e :object_type _object_type]
                                [?scan_profile :type "ScanProfile"]
                                [?scan_profile :reference ?e]
                                [?scan_profile :level _scan_level]
                                [?scan_profile :scan_profile_type _scan_profile_type]]
                        :limit {limit}
                        :offset {offset}
                    }}
                    :in-args [[{object_types}], [{scan_levels}], [{scan_profile_types}]]
                }}
        """.format(
            object_types=" ".join(map(lambda t: str_val(t.get_object_type()), types)),
            scan_levels=" ".join([str(scan_level.value) for scan_level in scan_levels]),
            scan_profile_types=" ".join([str_val(scan_profile_type.value) for scan_profile_type in scan_profile_types]),
            limit=limit,
            offset=offset,
        )

        res = self.session.client.query(data_query, valid_time)
        oois = [self.deserialize(x[0]) for x in res]
        return Paginated(
            count=count,
            items=oois,
        )

    def list_random(
        self, valid_time: datetime, amount: int = 1, scan_levels: Set[ScanLevel] = DEFAULT_SCAN_LEVEL_FILTER
    ) -> List[OOI]:
        query = """
            {{
                :query {{
                    :find [(rand {amount} ?id)]
                    :in [[_scan_level ...]]
                    :where [
                        [?e :crux.db/id ?id]
                        [?e :object_type]
                        [?scan_profile :type "ScanProfile"]
                        [?scan_profile :reference ?e]
                        [?scan_profile :level _scan_level]
                    ]
                }}
                :in-args [[{scan_levels}]]
            }}
            """.format(
            amount=amount,
            scan_levels=" ".join([str(scan_level.value) for scan_level in scan_levels]),
        )

        res = self.session.client.query(query, valid_time)
        if not res:
            return []
        references = {Reference.from_str(reference) for reference in res[0][0]}
        return list(self.load_bulk(references, valid_time).values())

    def get_tree(
        self,
        reference: Reference,
        valid_time: datetime,
        search_types: Optional[Set[Type[OOI]]] = None,
        depth: Optional[int] = 1,
    ) -> ReferenceTree:
        if search_types is None:
            search_types = {OOI}
        search_types = to_concrete(search_types)

        results = self._get_tree_level({reference}, depth=depth, valid_time=valid_time)

        try:
            reference_node = results[0]
        except IndexError:
            raise ObjectNotFoundException(str(reference))

        reference_node.filter_children(lambda child_node: child_node.reference.class_type in search_types)

        store = self.load_bulk(reference_node.collect_references(), valid_time)
        return ReferenceTree(root=reference_node, store=store)

    def _get_related_objects(self, references: Set[Reference], valid_time: Optional[datetime]) -> List[ReferenceNode]:
        """
        Returns a Reference node for each reference, containing the 1-depth related objects
        """
        ooi_classes = {ooi.class_ for ooi in references}
        ooi_ids = [str(reference) for reference in references]
        field_node = RelatedFieldNode(
            data_model=datamodel,
            object_types=ooi_classes,
        )
        field_node.build_tree(1)
        query = generate_pull_query(
            self.xtdb_type, FieldSet.ONLY_ID, {self.pk_prefix(): ooi_ids}, field_node=field_node
        )
        res = self.session.client.query(query, valid_time=valid_time)
        res = [element[0] for element in res]
        xtdb_reference_root_nodes = parse_obj_as(List[XTDBReferenceNode], res)
        return [x.to_reference_node(self.pk_prefix()) for x in xtdb_reference_root_nodes]

    def _get_tree_level(
        self,
        references: Set[Reference],
        depth: Optional[int] = 1,
        exclude: Optional[Set[Reference]] = None,
        valid_time: Optional[datetime] = None,
    ) -> List[ReferenceNode]:
        if depth == 0 or not references:
            return []

        if exclude is None:
            exclude = set()

        # Query 1-depth related objects
        reference_nodes = self._get_related_objects(references, valid_time=valid_time)

        # Filter exclusions from results
        for reference_node in reference_nodes:
            reference_node.filter_children(lambda child: child.reference not in exclude)

        if depth == 1:
            return reference_nodes

        # Next depth = children except non-traversable
        deeper_references: Set[Reference] = set()
        for reference_node in reference_nodes:
            for child_nodes in reference_node.children.values():
                deeper_references.update([child.reference for child in child_nodes])
        deeper_references = {reference for reference in deeper_references if reference.class_type.traversable()}

        # Query next level
        exclude.update(references)
        deeper_result = self._get_tree_level(deeper_references, depth=depth - 1, exclude=exclude, valid_time=valid_time)

        # Replace flat results with recursed results
        deeper_lookup = {node.reference: node for node in deeper_result}
        for node in reference_nodes:
            node.children = {
                attr_name: [deeper_lookup.get(child.reference, child) for child in children]
                for attr_name, children in node.children.items()
            }

        return reference_nodes

    @classmethod
    def encode_segment(cls, segment: Segment) -> str:
        if segment.direction == Direction.OUTGOING:
            return f"{segment.source_type.get_object_type()}/{segment.property_name}"
        else:
            return f"{segment.target_type.get_object_type()}/_{segment.property_name}"

    @classmethod
    def decode_segment(cls, encoded_segment: str) -> Segment:
        source_type_name, property_name = encoded_segment.split("/")
        relation_owner_type = type_by_name(source_type_name)

        if property_name.startswith("_"):
            direction = Direction.INCOMING
            property_name = property_name[1:]
            target_relation = get_relation(relation_owner_type, property_name)
            return Segment(target_relation, direction, property_name, relation_owner_type)
        else:
            direction = Direction.OUTGOING
            target_relation = get_relation(relation_owner_type, property_name)
            return Segment(relation_owner_type, direction, property_name, target_relation)

    @classmethod
    def construct_neighbour_query(cls, reference: Reference, paths: Optional[Set[Path]] = None) -> str:
        if paths is None:
            paths = get_paths_to_neighours(reference.class_type)

        encoded_segments = [cls.encode_segment(path.segments[0]) for path in sorted(paths)]
        segment_query_sections = [f"{{:{s} [*]}}" for s in encoded_segments]

        query = """{{
                    :query {{
                        :find [
                            (pull ?e [
                                :crux.db/id
                                {related_fields}
                            ])
                        ]
                        :in [[ _crux_db_id ... ]]
                        :where [[?e :crux.db/id _crux_db_id]]
                    }}
                    :in-args [["{reference}"]]
                }}""".format(
            reference=reference, related_fields=" ".join(segment_query_sections)
        )

        return query

    @classmethod
    def construct_neighbour_query_multi(cls, references: Set[Reference], paths: Set[Path]) -> str:
        encoded_segments = [cls.encode_segment(path.segments[0]) for path in sorted(paths)]
        segment_query_sections = [f"{{:{s} [*]}}" for s in encoded_segments]

        query = """{{
                        :query {{
                            :find [
                                (pull ?e [
                                    :crux.db/id
                                    {related_fields}
                                ])
                            ]
                            :in [[ _crux_db_id ... ]]
                            :where [[?e :crux.db/id _crux_db_id]]
                        }}
                        :in-args [[{reference}]]
                    }}""".format(
            reference=" ".join(map(str_val, references)), related_fields=" ".join(segment_query_sections)
        )

        return query

    def get_neighbours(
        self, reference: Reference, valid_time: datetime, paths: Set[Path] = None
    ) -> Dict[Path, List[OOI]]:
        query = self.construct_neighbour_query(reference, paths)

        response = self.session.client.query(query, valid_time=valid_time)

        try:
            response_data = response[0][0]
        except IndexError:
            return {}

        ret = {}
        for key, value in response_data.items():
            if key == "crux.db/id" or value == {}:
                continue
            path = Path([self.decode_segment(key)])
            if isinstance(value, list):
                ret[path] = [self.deserialize(serialized) for serialized in value]
            else:
                ret[path] = [self.deserialize(value)]

        return ret

    def list_neighbours(self, references: Set[Reference], paths: Set[Path], valid_time: datetime) -> Set[OOI]:
        query = self.construct_neighbour_query_multi(references, paths)

        response = self.session.client.query(query, valid_time=valid_time)

        neighbours = set()

        for row in response:
            col = row[0]
            for value in col.values():
                try:
                    if value:
                        if isinstance(value, list):
                            for serialized in value:
                                neighbours.add(self.deserialize(serialized))
                        else:
                            neighbours.add(self.deserialize(value))
                except ValueError:
                    # is not an error, old crux versions return the foreign key as a string,
                    # when related object is not found
                    logger.info("Could not deserialize value [value=%s]", value)

        return neighbours

    def save(self, ooi: OOI, valid_time: datetime, end_valid_time: Optional[datetime] = None) -> None:
        # retrieve old ooi
        try:
            old_ooi = self.get(ooi.reference, valid_time=valid_time)
        except ObjectNotFoundException:
            old_ooi = None

        new_ooi = ooi
        if old_ooi is not None:
            new_ooi, changed = merge_ooi(ooi, old_ooi)
            # Nothing changed, no need to save
            if not changed:
                return

        # save ooi with expiry
        self.session.add((XTDBOperationType.PUT, self.serialize(new_ooi), valid_time))
        if end_valid_time is not None:
            self.session.add((XTDBOperationType.DELETE, str(ooi.reference), end_valid_time))

        # Update event, instead of create
        event = OOIDBEvent(
            operation_type=OperationType.CREATE if old_ooi is None else OperationType.UPDATE,
            valid_time=valid_time,
            old_data=old_ooi,
            new_data=new_ooi,
        )

        # After transaction, send event
        self.session.listen_post_commit(lambda: self.event_manager.publish(event))

    def delete(self, reference: Reference, valid_time: datetime) -> None:
        # retrieve old ooi
        try:
            ooi = self.get(reference, valid_time=valid_time)
        except ObjectNotFoundException:
            return

        self.session.add((XTDBOperationType.DELETE, str(reference), valid_time))

        event = OOIDBEvent(
            operation_type=OperationType.DELETE,
            valid_time=valid_time,
            old_data=ooi,
        )
        self.session.listen_post_commit(lambda: self.event_manager.publish(event))

    def list_oois_without_scan_profile(self, valid_time: datetime) -> Set[Reference]:
        query = """
            {:query {
             :find [?ooi]
             :where [[?ooi :object_type ?t]
                    (not-join [?ooi] [?scan_profile :reference ?ooi] [?scan_profile :type "ScanProfile"])] }}
        """
        response = self.session.client.query(query, valid_time=valid_time)
        return {Reference.from_str(row[0]) for row in response}

    def count_findings_by_severity(self, valid_time: datetime) -> Counter:
        severity_counts = Counter({severity: 0 for severity in RiskLevelSeverity})

        query = """
            {:query {
                :find [?finding_type (pull ?finding_type [*]) (count ?finding)]
                :where [
                    [?finding :Finding/finding_type ?finding_type]
                    (not-join [?finding] [?muted_finding :MutedFinding/finding ?finding])
                    ]}}
        """

        for finding_type_name, finding_type_object, finding_count in self.session.client.query(
            str(query), valid_time=valid_time
        ):
            if not finding_type_object:
                logger.warning(
                    "There are %d %s findings but the finding type is not in the database",
                    finding_count,
                    finding_type_name,
                )
                severity = RiskLevelSeverity.PENDING
            else:
                ft = cast(FindingType, self.deserialize(finding_type_object))
                severity = ft.risk_severity or RiskLevelSeverity.PENDING
            severity_counts.update([severity] * finding_count)
        return severity_counts

    def get_bit_configs(self, source: OOI, bit_definition: BitDefinition, valid_time: datetime) -> List[Config]:
        path = Path.parse(f"{bit_definition.config_ooi_relation_path}.<ooi [is Config]")

        query = (
            Query.from_path(path)
            .where(type(source), primary_key=source.primary_key)
            .where(Config, bit_id=bit_definition.id)
        )

        configs = self.query(query, valid_time)

        return [config for config in configs if isinstance(config, Config)]

    def list_related(self, ooi: OOI, path: Path, valid_time: datetime) -> List[OOI]:
        path_start_alias = path.segments[0].source_type
        query = Query.from_path(path).where(path_start_alias, primary_key=ooi.primary_key)

        return self.query(query, valid_time)

    def list_findings(
        self,
        severities: Set[RiskLevelSeverity],
        exclude_muted=False,
        only_muted=False,
        offset=DEFAULT_OFFSET,
        limit=DEFAULT_LIMIT,
        valid_time: Optional[datetime] = None,
    ) -> Paginated[Finding]:
        # clause to find risk_severity
        concrete_finding_types = to_concrete({FindingType})
        severity_clauses = [
            f"[?finding_type :{finding_type.get_object_type()}/risk_severity ?severity]"
            for finding_type in concrete_finding_types
        ]
        or_severities = f"(or {' '.join(severity_clauses)})"

        # clause to find risk_score
        score_clauses = [
            f"[?finding_type :{finding_type.get_object_type()}/risk_score ?score]"
            for finding_type in concrete_finding_types
        ]
        or_scores = f"(or {' '.join(score_clauses)})"

        muted_clause = ""
        if exclude_muted:
            muted_clause = "(not-join [?finding] [?muted_finding :MutedFinding/finding ?finding])"
        elif only_muted:
            muted_clause = "[?muted_finding :MutedFinding/finding ?finding]"

        severity_values = ", ".join([str_val(severity.value) for severity in severities])

        count_query = f"""
            {{
                :query {{
                    :find [(count ?finding)]
                    :in [[severities_ ...]]
                    :where [[?finding :object_type "Finding"]
                            [?finding :Finding/finding_type ?finding_type]
                            [(== ?severity severities_)]
                            {or_severities}
                            {muted_clause}]
                }}
                :in-args [[{severity_values}]]
            }}
        """

        count_results = self.session.client.query(count_query, valid_time)
        count = 0
        if count_results and count_results[0]:
            count = count_results[0][0]

        finding_query = f"""
            {{
                :query {{
                    :find [(pull ?finding [*]) ?score]
                    :in [[severities_ ...]]
                    :where [[?finding :object_type "Finding"]
                            [?finding :Finding/finding_type ?finding_type]
                            [(== ?severity severities_)]
                            {or_severities}
                            {or_scores}
                            {muted_clause}]
                    :limit {limit}
                    :offset {offset}
                    :order-by [[?score :desc]]
                }}
               :in-args [[{severity_values}]]
            }}
        """

        res = self.session.client.query(finding_query, valid_time)
        findings = [self.deserialize(x[0]) for x in res]
        return Paginated(
            count=count,
            items=findings,
        )

    def query(self, query: Query, valid_time: datetime) -> List[OOI]:
        return [self.deserialize(row[0]) for row in self.session.client.query(str(query), valid_time=valid_time)]
