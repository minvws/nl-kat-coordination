from typing import List, Optional, Tuple

from scheduler import models

from ..stores import PriorityQueueStorer  # noqa: TID252
from .datastore import SQLAlchemy, retry


class PriorityQueueStore(PriorityQueueStorer):
    """Datastore for PriorityQueue.

    Exposes methods to interface with the database.

    Attributes:
        datastore: SQAlchemy satastore to use for the database connection.
    """

    def __init__(self, datastore: SQLAlchemy) -> None:
        super().__init__()

        self.datastore = datastore

    @retry()
    def pop(self, scheduler_id: str, filters: Optional[List[models.Filter]] = None) -> Optional[models.PrioritizedItem]:
        with self.datastore.session.begin() as session:
            query = session.query(models.PrioritizedItemORM).filter(
                models.PrioritizedItemORM.scheduler_id == scheduler_id
            )

            if filters is not None:
                for f in filters:
                    query = query.filter(models.PrioritizedItemORM.data[f.get_field()].as_string() == f.value)

            item_orm = query.first()

            if item_orm is None:
                return None

            return models.PrioritizedItem.from_orm(item_orm)

    @retry()
    def push(self, scheduler_id: str, item: models.PrioritizedItem) -> Optional[models.PrioritizedItem]:
        with self.datastore.session.begin() as session:
            item_orm = models.PrioritizedItemORM(**item.dict())
            session.add(item_orm)

            return models.PrioritizedItem.from_orm(item_orm)

    @retry()
    def peek(self, scheduler_id: str, index: int) -> Optional[models.PrioritizedItem]:
        with self.datastore.session.begin() as session:
            item_orm = (
                session.query(models.PrioritizedItemORM)
                .filter(models.PrioritizedItemORM.scheduler_id == scheduler_id)
                .order_by(models.PrioritizedItemORM.priority.asc())
                .order_by(models.PrioritizedItemORM.created_at.asc())
                .offset(index)
                .first()
            )

            if item_orm is None:
                return None

            return models.PrioritizedItem.from_orm(item_orm)

    @retry()
    def update(self, scheduler_id: str, item: models.PrioritizedItem) -> None:
        with self.datastore.session.begin() as session:
            (
                session.query(models.PrioritizedItemORM)
                .filter(models.PrioritizedItemORM.scheduler_id == scheduler_id)
                .filter(models.PrioritizedItemORM.id == item.id)
                .update(item.dict())
            )

    @retry()
    def remove(self, scheduler_id: str, item_id: str) -> None:
        with self.datastore.session.begin() as session:
            (
                session.query(models.PrioritizedItemORM)
                .filter(models.PrioritizedItemORM.scheduler_id == scheduler_id)
                .filter(models.PrioritizedItemORM.id == item_id)
                .delete()
            )

    @retry()
    def get(self, scheduler_id, item_id: str) -> Optional[models.PrioritizedItem]:
        with self.datastore.session.begin() as session:
            item_orm = (
                session.query(models.PrioritizedItemORM)
                .filter(models.PrioritizedItemORM.scheduler_id == scheduler_id)
                .filter(models.PrioritizedItemORM.id == item_id)
                .first()
            )

            if item_orm is None:
                return None

            return models.PrioritizedItem.from_orm(item_orm)

    @retry()
    def empty(self, scheduler_id: str) -> bool:
        with self.datastore.session.begin() as session:
            count = (
                session.query(models.PrioritizedItemORM)
                .filter(models.PrioritizedItemORM.scheduler_id == scheduler_id)
                .count()
            )
            return count == 0

    @retry()
    def qsize(self, scheduler_id: str) -> int:
        with self.datastore.session.begin() as session:
            count = (
                session.query(models.PrioritizedItemORM)
                .filter(models.PrioritizedItemORM.scheduler_id == scheduler_id)
                .count()
            )

            return count

    @retry()
    def get_items(
        self,
        scheduler_id: str,
        filters: Optional[List[models.Filter]] = None,
    ) -> Tuple[List[models.PrioritizedItem], int]:
        with self.datastore.session.begin() as session:
            query = session.query(models.PrioritizedItemORM).filter(
                models.PrioritizedItemORM.scheduler_id == scheduler_id
            )

            if filters is not None:
                for f in filters:
                    query = query.filter(models.PrioritizedItemORM.data[f.get_field()].astext == f.value)

            count = query.count()
            items_orm = query.all()

            return ([models.PrioritizedItem.from_orm(item_orm) for item_orm in items_orm], count)

    @retry()
    def get_item_by_hash(self, scheduler_id: str, item_hash: str) -> Optional[models.PrioritizedItem]:
        with self.datastore.session.begin() as session:
            item_orm = (
                session.query(models.PrioritizedItemORM)
                .order_by(models.PrioritizedItemORM.created_at.desc())
                .filter(models.PrioritizedItemORM.scheduler_id == scheduler_id)
                .filter(models.PrioritizedItemORM.hash == item_hash)
                .first()
            )

            if item_orm is None:
                return None

            return models.PrioritizedItem.from_orm(item_orm)

    @retry()
    def get_items_by_scheduler_id(self, scheduler_id: str) -> List[models.PrioritizedItem]:
        with self.datastore.session.begin() as session:
            items_orm = (
                session.query(models.PrioritizedItemORM)
                .filter(models.PrioritizedItemORM.scheduler_id == scheduler_id)
                .all()
            )

            return [models.PrioritizedItem.from_orm(item_orm) for item_orm in items_orm]

    @retry()
    def clear(self, scheduler_id: str) -> None:
        with self.datastore.session.begin() as session:
            (
                session.query(models.PrioritizedItemORM)
                .filter(models.PrioritizedItemORM.scheduler_id == scheduler_id)
                .delete()
            )
