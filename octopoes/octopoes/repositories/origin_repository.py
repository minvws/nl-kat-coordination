from datetime import datetime
from http import HTTPStatus
from logging import getLogger
from typing import Any, Dict, List, Optional
from uuid import UUID

from requests import HTTPError

from octopoes.config.settings import XTDBType
from octopoes.events.events import OperationType, OriginDBEvent
from octopoes.events.manager import EventManager
from octopoes.models import Reference
from octopoes.models.exception import ObjectNotFoundException
from octopoes.models.origin import Origin, OriginType
from octopoes.repositories.repository import Repository
from octopoes.xtdb import FieldSet
from octopoes.xtdb.client import OperationType as XTDBOperationType
from octopoes.xtdb.client import XTDBSession
from octopoes.xtdb.query_builder import generate_pull_query

logger = getLogger(__name__)


class OriginRepository(Repository):
    def __init__(self, event_manager: EventManager):
        self.event_manager = event_manager

    def get(self, origin_id: str, valid_time: datetime) -> Origin:
        raise NotImplementedError

    def save(self, origin: Origin, valid_time: datetime) -> None:
        raise NotImplementedError

    def list(
        self,
        valid_time: datetime,
        *,
        task_id: Optional[UUID] = None,
        source: Optional[Reference] = None,
        result: Optional[Reference] = None,
        origin_type: Optional[OriginType] = None,
    ) -> List[Origin]:
        raise NotImplementedError

    def delete(self, origin: Origin, valid_time: datetime) -> None:
        raise NotImplementedError


class XTDBOriginRepository(OriginRepository):
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
    def serialize(cls, origin: Origin) -> Dict[str, Any]:
        data = origin.dict()
        data[cls.pk_prefix()] = origin.id
        data["type"] = origin.__class__.__name__
        return data

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> Origin:
        return Origin.parse_obj(data)

    def list(
        self,
        valid_time: datetime,
        *,
        task_id: Optional[UUID] = None,
        source: Optional[Reference] = None,
        result: Optional[Reference] = None,
        origin_type: Optional[OriginType] = None,
    ) -> List[Origin]:
        where_parameters = {"type": Origin.__name__}

        if task_id:
            where_parameters["task_id"] = str(task_id)

        if source:
            where_parameters["source"] = str(source)

        if result:
            where_parameters["result"] = str(result)

        if origin_type:
            where_parameters["origin_type"] = origin_type.value

        query = generate_pull_query(
            self.xtdb_type,
            FieldSet.ALL_FIELDS,
            where_parameters,
        )

        results = self.session.client.query(query, valid_time=valid_time)
        return [self.deserialize(r[0]) for r in results]

    def get(self, id_: str, valid_time: datetime) -> Origin:
        try:
            return self.deserialize(self.session.client.get_entity(id_, valid_time))
        except HTTPError as e:
            if e.response.status_code == HTTPStatus.NOT_FOUND:
                raise ObjectNotFoundException(id_)
            else:
                raise e

    def save(self, origin: Origin, valid_time: datetime) -> None:
        try:
            old_origin = self.get(origin.id, valid_time)
        except ObjectNotFoundException:
            old_origin = None

        if old_origin == origin:
            # Declared and inferered origins won't have a task id, so if the old
            # origin is the same as the one being saved we can just return. In
            # case an observed origin is saved, we will delete the origin with
            # the old task id and create a new one. We can still fetch the old
            # origin using the previous valid time.
            if origin.task_id == old_origin.task_id:
                return

            self.session.add((XTDBOperationType.DELETE, old_origin.id, valid_time))

        self.session.add((XTDBOperationType.PUT, self.serialize(origin), valid_time))

        if old_origin != origin:
            # Only publish an event if there is a change in data. We won't send
            # events when only the normalizer task id of an observed origin is
            # updated.
            event = OriginDBEvent(
                operation_type=OperationType.CREATE if old_origin is None else OperationType.UPDATE,
                valid_time=valid_time,
                old_data=old_origin,
                new_data=origin,
            )
            self.session.listen_post_commit(lambda: self.event_manager.publish(event))

    def delete(self, origin: Origin, valid_time: datetime) -> None:
        self.session.add((XTDBOperationType.DELETE, origin.id, valid_time))

        event = OriginDBEvent(
            operation_type=OperationType.DELETE,
            valid_time=valid_time,
            old_data=origin,
        )
        self.session.listen_post_commit(lambda: self.event_manager.publish(event))
