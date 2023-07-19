from datetime import datetime
from http import HTTPStatus
from logging import getLogger
from typing import Any, Dict, List, Optional, Set

from pydantic import parse_obj_as
from requests import HTTPError

from octopoes.config.settings import XTDBType
from octopoes.events.events import OperationType, ScanProfileDBEvent
from octopoes.events.manager import EventManager
from octopoes.models import (
    Reference,
    ScanProfile,
    ScanProfileBase,
)
from octopoes.models.exception import ObjectNotFoundException
from octopoes.xtdb import FieldSet
from octopoes.xtdb.client import OperationType as XTDBOperationType
from octopoes.xtdb.client import XTDBSession
from octopoes.xtdb.query_builder import generate_pull_query

logger = getLogger(__name__)


class ScanProfileRepository:
    def __init__(self, event_manager: EventManager):
        self.event_manager = event_manager

    def get(self, ooi_reference: Reference, valid_time: datetime) -> ScanProfileBase:
        raise NotImplementedError

    def save(
        self, old_scan_profile: Optional[ScanProfileBase], new_scan_profile: ScanProfileBase, valid_time: datetime
    ) -> None:
        raise NotImplementedError

    def list(self, scan_profile_type: Optional[str], valid_time: datetime) -> List[ScanProfileBase]:
        raise NotImplementedError

    def delete(self, scan_profile: ScanProfileBase, valid_time: datetime) -> None:
        raise NotImplementedError

    def get_bulk(self, references: Set[Reference], valid_time: datetime) -> List[ScanProfileBase]:
        raise NotImplementedError


class XTDBScanProfileRepository(ScanProfileRepository):
    xtdb_type: XTDBType = XTDBType.XTDB_MULTINODE

    def __init__(self, event_manager: EventManager, session: XTDBSession, xtdb_type: XTDBType):
        super().__init__(event_manager)
        self.session = session
        self.__class__.xtdb_type = xtdb_type

    @classmethod
    def pk_prefix(cls):
        return "xt/id"

    @classmethod
    def object_type(cls):
        return "ScanProfile"

    @classmethod
    def format_id(cls, ooi_reference: Reference):
        return f"{cls.object_type()}|{ooi_reference}"

    @classmethod
    def serialize(cls, scan_profile: ScanProfile) -> Dict[str, Any]:
        data = scan_profile.dict()
        data[cls.pk_prefix()] = cls.format_id(scan_profile.reference)
        data["type"] = cls.object_type()
        return data

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> ScanProfileBase:
        return parse_obj_as(ScanProfile, data)

    def list(self, scan_profile_type: Optional[str], valid_time: datetime) -> List[ScanProfileBase]:
        where = {"type": self.object_type()}
        if scan_profile_type is not None:
            where["scan_profile_type"] = scan_profile_type
        query = generate_pull_query(
            self.xtdb_type,
            FieldSet.ALL_FIELDS,
            where,
        )
        results = self.session.client.query(query, valid_time=valid_time)
        return [self.deserialize(r[0]) for r in results]

    def get(self, ooi_reference: Reference, valid_time: datetime) -> ScanProfileBase:
        id_ = self.format_id(ooi_reference)
        try:
            return self.deserialize(self.session.client.get_entity(id_, valid_time))
        except HTTPError as e:
            if e.response.status_code == HTTPStatus.NOT_FOUND:
                raise ObjectNotFoundException(id_)
            else:
                raise e

    def save(
        self, old_scan_profile: Optional[ScanProfileBase], new_scan_profile: ScanProfileBase, valid_time: datetime
    ) -> None:
        if old_scan_profile == new_scan_profile:
            return
        self.session.add((XTDBOperationType.PUT, self.serialize(new_scan_profile), valid_time))

        event = ScanProfileDBEvent(
            operation_type=OperationType.CREATE if old_scan_profile is None else OperationType.UPDATE,
            valid_time=valid_time,
            reference=new_scan_profile.reference,
            old_data=old_scan_profile,
            new_data=new_scan_profile,
        )
        self.session.listen_post_commit(lambda: self.event_manager.publish(event))

    def delete(self, scan_profile: ScanProfileBase, valid_time: datetime) -> None:
        self.session.add((XTDBOperationType.DELETE, self.format_id(scan_profile.reference), valid_time))

        event = ScanProfileDBEvent(
            operation_type=OperationType.DELETE,
            reference=scan_profile.reference,
            valid_time=valid_time,
            old_data=scan_profile,
        )
        self.session.listen_post_commit(lambda: self.event_manager.publish(event))

    def get_bulk(self, references: Set[Reference], valid_time: datetime) -> List[ScanProfileBase]:
        ids = list(map(str, references))
        query = generate_pull_query(self.xtdb_type, FieldSet.ALL_FIELDS, {"type": self.object_type(), "reference": ids})
        res = self.session.client.query(query, valid_time)
        return [self.deserialize(x[0]) for x in res]
