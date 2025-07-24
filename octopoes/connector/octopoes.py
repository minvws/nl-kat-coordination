import json
import uuid
from collections.abc import Iterable, Sequence
from datetime import datetime
from operator import itemgetter
from typing import Any, Literal
from uuid import UUID

import structlog
from django.conf import settings
from pydantic import TypeAdapter

from octopoes.api.models import Affirmation, Declaration, Observation
from octopoes.core.app import bootstrap_octopoes, get_xtdb_client
from octopoes.events.manager import EventManager
from octopoes.models import OOI, Reference, ScanLevel, ScanProfile, ScanProfileType
from octopoes.models.exception import ObjectNotFoundException
from octopoes.models.explanation import InheritanceSection
from octopoes.models.ooi.findings import Finding, RiskLevelSeverity
from octopoes.models.ooi.reports import HydratedReport
from octopoes.models.origin import Origin, OriginParameter, OriginType
from octopoes.models.pagination import Paginated
from octopoes.models.path import Path
from octopoes.models.transaction import TransactionRecord
from octopoes.models.tree import ReferenceTree
from octopoes.models.types import OOIType, type_by_name
from octopoes.repositories.ooi_repository import XTDBOOIRepository
from octopoes.repositories.scan_profile_repository import XTDBScanProfileRepository
from octopoes.types import OBJECT_DELETED, ORIGIN_DELETED
from octopoes.xtdb.client import Operation, OperationType, XTDBSession
from octopoes.xtdb.exceptions import XTDBException
from octopoes.xtdb.query import Aliased, Query
from openkat.exceptions import OctopoesException

HydratedReportTypeAdapter = TypeAdapter(dict[UUID, HydratedReport])
logger = structlog.get_logger(__name__)


class OctopoesAPIConnector:
    """
    Methods on this Connector can throw
        - httpx.HTTPError if HTTP connection to Octopoes API fails
        - connector.ObjectNotFoundException if the OOI node cannot be found
        - connector.RemoteException if an error occurs inside Octopoes API
    """

    def __init__(self, client: str, xtdb_uri: str):
        self.xtdb_uri = xtdb_uri
        self.xtdb_session = XTDBSession(get_xtdb_client(self.xtdb_uri, client))
        self.octopoes = bootstrap_octopoes(client, self.xtdb_session)

    def list_objects(
        self,
        types: set[type[OOI]] | set[str],
        valid_time: datetime,
        offset: int = settings.DEFAULT_OFFSET,
        limit: int = settings.DEFAULT_LIMIT,
        scan_level: set[ScanLevel] = settings.DEFAULT_SCAN_LEVEL_FILTER,
        scan_profile_type: set[ScanProfileType] = settings.DEFAULT_SCAN_PROFILE_TYPE_FILTER,
        search_string: str | None = None,
        order_by: Literal["scan_level", "object_type"] = "object_type",
        asc_desc: Literal["asc", "desc"] = "asc",
    ) -> Paginated[OOI]:
        return self.octopoes.list_ooi(
            types={type_by_name(t) if isinstance(t, str) else t for t in types},
            valid_time=valid_time,
            offset=offset,
            limit=limit,
            scan_levels=scan_level,
            scan_profile_types=scan_profile_type,
            search_string=search_string,
            order_by=order_by,
            asc_desc=asc_desc,
        )

    def get(self, reference: Reference | str, valid_time: datetime) -> OOI:
        return self.octopoes.get_ooi(reference, valid_time)

    def get_history(
        self,
        reference: Reference,
        *,
        sort_order: str = "asc",  # Or: "desc"
        with_docs: bool = False,
        has_doc: bool | None = None,
        offset: int = 0,
        limit: int | None = None,
        indices: list[int] | None = None,
    ) -> list[TransactionRecord]:
        return self.octopoes.get_ooi_history(
            reference,
            sort_order=sort_order,
            with_docs=with_docs,
            has_doc=has_doc,
            offset=offset,
            limit=limit,
            indices=indices,
        )

    def get_tree(
        self, reference: Reference, valid_time: datetime, types: set | None = None, depth: int = 1
    ) -> ReferenceTree:
        return self.octopoes.get_ooi_tree(reference, valid_time, types, depth)

    def list_origins(
        self,
        valid_time: datetime,
        offset: int = settings.DEFAULT_OFFSET,
        limit: int = settings.DEFAULT_LIMIT,
        source: Reference | None = None,
        result: Reference | None = None,
        method: str | list[str] | None = None,
        task_id: UUID | None = None,
        origin_type: OriginType | None = None,
    ) -> list[Origin]:
        logger.info("query %s %s", valid_time, task_id)
        return self.octopoes.origin_repository.list_origins(
            valid_time,
            task_id=task_id,
            offset=offset,
            limit=limit,
            source=source,
            result=result,
            method=method,
            origin_type=str(origin_type.value) if origin_type else None,
        )

    def delete_origin(self, origin_id: str, valid_time: datetime) -> None:
        origin = self.octopoes.origin_repository.get(origin_id, valid_time)
        self.octopoes.origin_repository.delete(origin, valid_time)
        self.octopoes.commit()
        logger.info("Deleted origin", origin_id=origin_id, valid_time=valid_time, event_code=ORIGIN_DELETED)

    def save_observation(self, observation: Observation) -> None:
        origin = Origin(
            origin_type=OriginType.OBSERVATION,
            method=observation.method,
            source=observation.source,
            source_method=observation.source_method,
            result=[ooi.reference for ooi in observation.result],
            task_id=observation.task_id,
        )
        self.octopoes.save_origin(origin, observation.result, observation.valid_time)
        self.octopoes.commit()

    def save_declaration(self, declaration: Declaration) -> None:
        origin = Origin(
            origin_type=OriginType.DECLARATION,
            method=declaration.method if declaration.method else "manual",
            source=declaration.ooi.reference,
            source_method=declaration.source_method,
            result=[declaration.ooi.reference],
            task_id=declaration.task_id if declaration.task_id else uuid.uuid4(),
        )
        self.octopoes.save_origin(origin, [declaration.ooi], declaration.valid_time, declaration.end_valid_time)
        self.octopoes.commit()

    def save_many_declarations(self, declarations: list[Declaration]) -> None:
        for declaration in declarations:
            origin = Origin(
                origin_type=OriginType.DECLARATION,
                method=declaration.method if declaration.method else "manual",
                source=declaration.ooi.reference,
                source_method=declaration.source_method,
                result=[declaration.ooi.reference],
                task_id=declaration.task_id if declaration.task_id else uuid.uuid4(),
            )
            self.octopoes.save_origin(origin, [declaration.ooi], declaration.valid_time, declaration.end_valid_time)
            self.octopoes.commit()

    def save_affirmation(self, affirmation: Affirmation) -> None:
        origin = Origin(
            origin_type=OriginType.AFFIRMATION,
            method=affirmation.method if affirmation.method else "hydration",
            source=affirmation.ooi.reference,
            source_method=affirmation.source_method,
            result=[affirmation.ooi.reference],
            task_id=affirmation.task_id if affirmation.task_id else uuid.uuid4(),
        )
        self.octopoes.save_origin(origin, [affirmation.ooi], affirmation.valid_time)
        self.octopoes.commit()

    def save_scan_profile(self, scan_profile: ScanProfile, valid_time: datetime) -> None:
        try:
            old_scan_profile = self.octopoes.scan_profile_repository.get(scan_profile.reference, valid_time)
        except ObjectNotFoundException:
            old_scan_profile = None

        self.octopoes.scan_profile_repository.save(old_scan_profile, scan_profile, valid_time)
        self.octopoes.commit()

    def save_many_scan_profiles(self, scan_profiles: list[ScanProfile], valid_time: datetime) -> None:
        for scan_profile in scan_profiles:
            try:
                old_scan_profile = self.octopoes.scan_profile_repository.get(scan_profile.reference, valid_time)
            except ObjectNotFoundException:
                old_scan_profile = None

            self.octopoes.scan_profile_repository.save(old_scan_profile, scan_profile, valid_time)

        self.octopoes.commit()

    def delete(self, reference: Reference, valid_time: datetime) -> None:
        self.octopoes.ooi_repository.delete(reference, valid_time)
        self.octopoes.commit()

        logger.info("Deleted object", reference=reference, valid_time=valid_time, event_code=OBJECT_DELETED)

    def delete_many(self, references: list[Reference] | list[str], valid_time: datetime) -> None:
        for reference in references:
            self.octopoes.ooi_repository.delete(reference, valid_time)

        self.octopoes.commit()
        logger.info("Deleted objects", references=references, valid_time=valid_time)

    def list_origin_parameters(self, origin_id: set[str], valid_time: datetime) -> list[OriginParameter]:
        return self.octopoes.origin_parameter_repository.list_by_origin(origin_id, valid_time)

    def create_node(self):
        self.xtdb_session.client.create_node()
        logger.info("Created node")

    def delete_node(self):
        self.xtdb_session.client.delete_node()
        self.xtdb_session.commit()
        logger.info("Deleted node")

    def get_scan_profile_inheritance(self, reference: Reference, valid_time: datetime) -> list[InheritanceSection]:
        ooi = self.octopoes.get_ooi(reference, valid_time)
        if not ooi.scan_profile:
            raise OctopoesException("OOI does not have a scanprofile")

        start = InheritanceSection(
            reference=ooi.reference, level=ooi.scan_profile.level, scan_profile_type=ooi.scan_profile.scan_profile_type
        )
        if ooi.scan_profile.scan_profile_type == ScanProfileType.DECLARED.value:
            return [start]

        return self.octopoes.get_scan_profile_inheritance(reference, valid_time, [start])

    def list_findings(
        self,
        severities: Iterable[RiskLevelSeverity],
        valid_time: datetime,
        exclude_muted: bool = True,
        only_muted: bool = False,
        offset: int = settings.DEFAULT_OFFSET,
        limit: int = settings.DEFAULT_LIMIT,
        search_string: str | None = None,
        order_by: Literal["score", "finding_type"] = "score",
        asc_desc: Literal["asc", "desc"] = "desc",
    ) -> Paginated[Finding]:
        return self.octopoes.ooi_repository.list_findings(
            set(severities), valid_time, exclude_muted, only_muted, offset, limit, search_string, order_by, asc_desc
        )

    def list_reports(
        self,
        valid_time: datetime,
        offset: int = settings.DEFAULT_OFFSET,
        limit: int = settings.DEFAULT_LIMIT,
        recipe_id: UUID | None = None,
    ) -> Paginated[HydratedReport]:
        return self.octopoes.ooi_repository.list_reports(valid_time, offset, limit, recipe_id)

    def bulk_list_reports(
        self, valid_time: datetime, reports_filters: list[tuple[str, str]]
    ) -> dict[str, HydratedReport]:
        """
        An efficient method for getting reports across organizations
        """

        # The reason for creating the event_manager do this in the loop is the '_try_connect()' call in the __init__
        # possibly slowing this down, while this API was introduced to improve performance. Simply reusing it for all
        # clients works because the event manager is only used in callbacks triggered on a `commit()`, while these
        # queries are read-only and hence don't need a `commit()` as no events would be triggered. (A cleaner solution
        # would perhaps be to extract an interface and pass a new NullManager.)
        event_manager = EventManager("null", "", settings.QUEUE_NAME_OCTOPOES)

        # The xtdb_http_client is also created outside the loop and the `_client` property changed inside the loop
        # instead, to reuse the httpx Session for all requests.
        xtdb_http_client = get_xtdb_client(str(settings.XTDB_URI), "")
        xtdb_session = XTDBSession(xtdb_http_client)
        ooi_repository = XTDBOOIRepository(
            event_manager, xtdb_session, XTDBScanProfileRepository(event_manager, xtdb_session)
        )

        reports = {}

        for client, recipe_id in reports_filters:
            xtdb_http_client.client = client

            for report in ooi_repository.list_reports(valid_time, 0, 1, recipe_id, ignore_count=True).items:
                reports[recipe_id] = report

        return reports

    def list_object_clients(self, reference: Reference, clients: set[str], valid_time: datetime) -> dict[str, OOIType]:
        """
        An efficient endpoint for checking if OOIs live in multiple organizations
        """

        # See list_reports() for some of the reasoning behind the below code
        xtdb_http_client = get_xtdb_client(self.xtdb_uri, "")
        session = XTDBSession(xtdb_http_client)

        octopoes = bootstrap_octopoes("null", session)
        clients_with_reference = {}

        for client in clients:
            xtdb_http_client.client = client

            try:
                ooi = octopoes.get_ooi(reference, valid_time)
            except ObjectNotFoundException:
                continue

            clients_with_reference[client] = ooi

        return clients_with_reference

    def get_report(self, report_id: str, valid_time: datetime) -> HydratedReport:
        return self.octopoes.ooi_repository.get_report(valid_time, report_id)

    def load_objects_bulk(self, references: set[Reference | str], valid_time: datetime) -> dict[Reference, OOIType]:
        return self.octopoes.ooi_repository.load_bulk(references, valid_time)

    def recalculate_bits(self) -> int:
        count = self.octopoes.recalculate_bits()
        self.octopoes.commit()

        return count

    def query(
        self,
        path: str,
        valid_time: datetime,
        source: OOI | Reference | str | None = None,
        offset: int = settings.DEFAULT_OFFSET,
        limit: int = settings.DEFAULT_LIMIT,
    ) -> list[OOI]:
        object_path = Path.parse(path)
        xtdb_query = Query.from_path(object_path).offset(offset).limit(limit)

        if source is not None and object_path.segments:
            xtdb_query = xtdb_query.where(object_path.segments[0].source_type, primary_key=str(source))

        return self.octopoes.ooi_repository.query(xtdb_query, valid_time)  # type: ignore

    def query_many(
        self, path: str, valid_time: datetime, sources: Sequence[OOI | Reference | str]
    ) -> list[tuple[str, OOIType]]:
        """
        How does this work and why do we do this?

        We want to fetch all results but be able to tie these back to the source that was used for a result.
        If we query "Network.hostname" for a list of Networks ids, how do we know which hostname lives on which network?
        The answer is to add the network id to the "select" statement, so the result is of the form

           [(network_id_1, hostname1), (network_id_2, hostname3), ...]

        Because you can only select variables in Datalog, "network_id_1" needs to be an Alias. Hence `source_alias`.
        We need to tie that to the Network primary_key and add a where-in clause. The example projected on the code:

        q = XTDBQuery.from_path(object_path)                                  # Adds "where ?Hostname.network = ?Network

        q.find(source_alias).pull(query.result_type)                          # "select ?network_id, ?Hostname
        .where(object_path.segments[0].source_type, primary_key=source_alias) # where ?Network.primary_key = ?network_id
        .where_in(object_path.segments[0].source_type, primary_key=sources)   # and ?Network.primary_key in ["1", ...]"
        """

        if not sources:
            return []

        sources = [source.reference if isinstance(source, OOI) else source for source in sources]

        object_path = Path.parse(path)
        if not object_path.segments:
            raise OctopoesException("No path components provided.")

        q = Query.from_path(object_path)
        source_alias = Aliased(object_path.segments[0].source_type, field="primary_key")

        q = q.where(object_path.segments[0].source_type, primary_key=source_alias).where_in(
            object_path.segments[0].source_type, primary_key=sources
        )

        if q._find_clauses:  # Path contained a target field, so no need to pull the result type
            return self.octopoes.ooi_repository.query(q.find(source_alias, index=0), valid_time)  # type: ignore

        return self.octopoes.ooi_repository.query(q.find(source_alias, index=0).pull(q.result_type), valid_time)  # type: ignore

    def export_all(self):
        return self.xtdb_session.client.export_transactions()

    def import_add(self, content):
        return importer(content, self.xtdb_session)

    def import_new(self, content):
        return importer(content, self.xtdb_session, True)


def importer(data: bytes, xtdb_session_: XTDBSession, reset: bool = False) -> dict[str, int]:
    try:
        ops: list[dict[str, Any]] = list(map(itemgetter("txOps"), json.loads(data)))
    except Exception as e:
        logger.debug("Error parsing objects", exc_info=True)
        raise OctopoesException("Error parsing objects") from e
    if reset:
        try:
            xtdb_session_.client.delete_node()
            xtdb_session_.client.create_node()
            xtdb_session_.commit()
        except XTDBException as e:
            raise OctopoesException("Error recreating nodes") from e
    for op in ops:
        try:
            operations: list[Operation] = [
                (OperationType(x[0]), x[1], datetime.strptime(x[2], "%Y-%m-%dT%H:%M:%SZ")) for x in op
            ]
            xtdb_session_.client.submit_transaction(operations)
        except Exception as e:
            logger.debug("Error importing objects", exc_info=True)
            raise OctopoesException(f"Error importing object {op}") from e

    return {"detail": len(ops)}
