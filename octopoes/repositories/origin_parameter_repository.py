from datetime import datetime
from http import HTTPStatus
from logging import getLogger
from typing import Any, Dict, List

from requests import HTTPError

from octopoes.config.settings import XTDBType
from octopoes.events.events import OperationType, OriginParameterDBEvent
from octopoes.events.manager import EventManager
from octopoes.models import Reference
from octopoes.models.exception import ObjectNotFoundException
from octopoes.models.origin import OriginParameter
from octopoes.xtdb import FieldSet
from octopoes.xtdb.client import XTDBSession, OperationType as XTDBOperationType
from octopoes.xtdb.query_builder import generate_pull_query

logger = getLogger(__name__)


class OriginParameterRepository:
    def __init__(self, event_manager: EventManager):
        self.event_manager = event_manager

    def get(self, origin_parameter_id: str, valid_time: datetime) -> OriginParameter:
        raise NotImplementedError

    def save(self, origin_parameter: OriginParameter, valid_time: datetime) -> None:
        raise NotImplementedError

    def delete(self, origin_parameter: OriginParameter, valid_time: datetime) -> None:
        raise NotImplementedError

    def list_by_origin(self, origin_id: str, valid_time: datetime) -> List[OriginParameter]:
        raise NotImplementedError

    def list_by_reference(self, reference: Reference, valid_time: datetime) -> List[OriginParameter]:
        raise NotImplementedError


class XTDBOriginParameterRepository(OriginParameterRepository):

    xtdb_type: XTDBType = XTDBType.CRUX

    def __init__(self, event_manager: EventManager, session: XTDBSession, xtdb_type: XTDBType):
        super().__init__(event_manager)
        self.session = session
        self.__class__.xtdb_type = xtdb_type

    @classmethod
    def pk_prefix(cls):
        return "crux.db/id" if cls.xtdb_type == XTDBType.CRUX else "xt/id"

    @classmethod
    def serialize(cls, origin_parameter: OriginParameter) -> Dict[str, Any]:
        data = origin_parameter.dict()
        data[cls.pk_prefix()] = origin_parameter.id
        data["type"] = origin_parameter.__class__.__name__
        return data

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> OriginParameter:
        return OriginParameter.parse_obj(data)

    def get(self, id_: str, valid_time: datetime) -> OriginParameter:
        try:
            return self.deserialize(self.session.client.get_entity(id_, valid_time))
        except HTTPError as e:
            if e.response.status_code == HTTPStatus.NOT_FOUND:
                raise ObjectNotFoundException(id_)
            else:
                raise e

    def list_by_origin(self, origin_id: str, valid_time: datetime) -> List[OriginParameter]:
        query = generate_pull_query(
            self.xtdb_type,
            FieldSet.ALL_FIELDS,
            {
                "origin_id": str(origin_id),
                "type": OriginParameter.__name__,
            },
        )
        results = self.session.client.query(query, valid_time=valid_time)
        return [self.deserialize(r[0]) for r in results]

    def list_by_reference(self, reference: Reference, valid_time: datetime):
        query = generate_pull_query(
            self.xtdb_type,
            FieldSet.ALL_FIELDS,
            {
                "reference": str(reference),
                "type": OriginParameter.__name__,
            },
        )
        results = self.session.client.query(query, valid_time=valid_time)
        return [self.deserialize(r[0]) for r in results]

    def save(self, origin_parameter: OriginParameter, valid_time: datetime) -> None:
        old_origin_parameter = None
        try:
            old_origin_parameter = self.get(origin_parameter.id, valid_time)
        except ObjectNotFoundException:
            pass

        if old_origin_parameter == origin_parameter:
            return

        self.session.add((XTDBOperationType.PUT, self.serialize(origin_parameter), valid_time))

        event = OriginParameterDBEvent(
            operation_type=OperationType.CREATE if old_origin_parameter is None else OperationType.UPDATE,
            valid_time=valid_time,
            old_data=old_origin_parameter,
            new_data=origin_parameter,
        )
        self.session.listen_post_commit(lambda: self.event_manager.publish(event))

    def delete(self, origin_parameter: OriginParameter, valid_time: datetime) -> None:
        self.session.add((XTDBOperationType.DELETE, origin_parameter.id, valid_time))

        event = OriginParameterDBEvent(
            operation_type=OperationType.DELETE,
            valid_time=valid_time,
            old_data=origin_parameter,
        )
        self.session.listen_post_commit(lambda: self.event_manager.publish(event))
