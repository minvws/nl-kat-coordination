from typing import List, Optional, Tuple
from uuid import UUID

from scheduler import models

from .storage import DBConn, retry


class PriorityQueueStore:
    name: str = "pq_store"

    def __init__(self, dbconn: DBConn) -> None:
        self.dbconn = dbconn

    @retry()
    def pop(self, scheduler_id: str, filters: Optional[List[models.Filter]] = None) -> Optional[models.PrioritizedItem]:
        with self.dbconn.session.begin() as session:
            query = session.query(models.PrioritizedItemDB).filter(
                models.PrioritizedItemDB.scheduler_id == scheduler_id
            )

            if filters is not None:
                for f in filters:
                    query = query.filter(models.PrioritizedItemDB.data[f.get_field()].as_string() == f.value)

            item_orm = query.first()

            if item_orm is None:
                return None

            return models.PrioritizedItem.model_validate(item_orm)

    @retry()
    def push(self, scheduler_id: str, item: models.PrioritizedItem) -> Optional[models.PrioritizedItem]:
        with self.dbconn.session.begin() as session:
            item_orm = models.PrioritizedItemDB(**item.model_dump())
            session.add(item_orm)

            return models.PrioritizedItem.model_validate(item_orm)

    @retry()
    def peek(self, scheduler_id: str, index: int) -> Optional[models.PrioritizedItem]:
        with self.dbconn.session.begin() as session:
            item_orm = (
                session.query(models.PrioritizedItemDB)
                .filter(models.PrioritizedItemDB.scheduler_id == scheduler_id)
                .order_by(models.PrioritizedItemDB.priority.asc())
                .order_by(models.PrioritizedItemDB.created_at.asc())
                .offset(index)
                .first()
            )

            if item_orm is None:
                return None

            return models.PrioritizedItem.model_validate(item_orm)

    @retry()
    def update(self, scheduler_id: str, item: models.PrioritizedItem) -> None:
        with self.dbconn.session.begin() as session:
            (
                session.query(models.PrioritizedItemDB)
                .filter(models.PrioritizedItemDB.scheduler_id == scheduler_id)
                .filter(models.PrioritizedItemDB.id == item.id)
                .update(item.model_dump())
            )

    @retry()
    def remove(self, scheduler_id: str, item_id: UUID) -> None:
        with self.dbconn.session.begin() as session:
            (
                session.query(models.PrioritizedItemDB)
                .filter(models.PrioritizedItemDB.scheduler_id == scheduler_id)
                .filter(models.PrioritizedItemDB.id == str(item_id))
                .delete()
            )

    @retry()
    def get(self, scheduler_id, item_id: UUID) -> Optional[models.PrioritizedItem]:
        with self.dbconn.session.begin() as session:
            item_orm = (
                session.query(models.PrioritizedItemDB)
                .filter(models.PrioritizedItemDB.scheduler_id == scheduler_id)
                .filter(models.PrioritizedItemDB.id == str(item_id))
                .first()
            )

            if item_orm is None:
                return None

            return models.PrioritizedItem.model_validate(item_orm)

    @retry()
    def empty(self, scheduler_id: str) -> bool:
        with self.dbconn.session.begin() as session:
            count = (
                session.query(models.PrioritizedItemDB)
                .filter(models.PrioritizedItemDB.scheduler_id == scheduler_id)
                .count()
            )
            return count == 0

    @retry()
    def qsize(self, scheduler_id: str) -> int:
        with self.dbconn.session.begin() as session:
            count = (
                session.query(models.PrioritizedItemDB)
                .filter(models.PrioritizedItemDB.scheduler_id == scheduler_id)
                .count()
            )

            return count

    @retry()
    def get_items(
        self,
        scheduler_id: str,
        filters: Optional[List[models.Filter]] = None,
    ) -> Tuple[List[models.PrioritizedItem], int]:
        with self.dbconn.session.begin() as session:
            query = session.query(models.PrioritizedItemDB).filter(
                models.PrioritizedItemDB.scheduler_id == scheduler_id
            )

            if filters is not None:
                for f in filters:
                    query = query.filter(models.PrioritizedItemDB.data[f.get_field()].astext == f.value)

            count = query.count()
            items_orm = query.all()

            return ([models.PrioritizedItem.model_validate(item_orm) for item_orm in items_orm], count)

    @retry()
    def get_item_by_hash(self, scheduler_id: str, item_hash: str) -> Optional[models.PrioritizedItem]:
        with self.dbconn.session.begin() as session:
            item_orm = (
                session.query(models.PrioritizedItemDB)
                .order_by(models.PrioritizedItemDB.created_at.desc())
                .filter(models.PrioritizedItemDB.scheduler_id == scheduler_id)
                .filter(models.PrioritizedItemDB.hash == item_hash)
                .first()
            )

            if item_orm is None:
                return None

            return models.PrioritizedItem.model_validate(item_orm)

    @retry()
    def get_items_by_scheduler_id(self, scheduler_id: str) -> List[models.PrioritizedItem]:
        with self.dbconn.session.begin() as session:
            items_orm = (
                session.query(models.PrioritizedItemDB)
                .filter(models.PrioritizedItemDB.scheduler_id == scheduler_id)
                .all()
            )

            return [models.PrioritizedItem.model_validate(item_orm) for item_orm in items_orm]

    @retry()
    def clear(self, scheduler_id: str) -> None:
        with self.dbconn.session.begin() as session:
            (
                session.query(models.PrioritizedItemDB)
                .filter(models.PrioritizedItemDB.scheduler_id == scheduler_id)
                .delete()
            )
