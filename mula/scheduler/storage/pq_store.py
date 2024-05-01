from uuid import UUID

from scheduler import models

from .filters import FilterRequest, apply_filter
from .storage import DBConn, retry


class PriorityQueueStore:
    name: str = "pq_store"

    def __init__(self, dbconn: DBConn) -> None:
        self.dbconn = dbconn

    @retry()
    def pop(self, scheduler_id: str, filters: FilterRequest | None = None) -> models.Task | None:
        with self.dbconn.session.begin() as session:
            query = (
                session.query(models.TaskDB)
                .filter(models.TaskDB.status == models.TaskStatus.QUEUED)
                .order_by(models.TaskDB.priority.asc())
                .order_by(models.TaskDB.created_at.asc())
                .filter(models.TaskDB.scheduler_id == scheduler_id)
            )

            if filters is not None:
                query = apply_filter(models.TaskDB, query, filters)

            item_orm = query.first()

            if item_orm is None:
                return None

            return models.Task.model_validate(item_orm)

    @retry()
    def push(self, scheduler_id: str, item: models.Task) -> models.Task | None:
        with self.dbconn.session.begin() as session:
            item_orm = models.TaskDB(**item.model_dump())
            session.add(item_orm)

            return models.Task.model_validate(item_orm)

    @retry()
    def peek(self, scheduler_id: str, index: int) -> models.Task | None:
        with self.dbconn.session.begin() as session:
            item_orm = (
                session.query(models.TaskDB)
                .filter(models.TaskDB.status == models.TaskStatus.QUEUED)
                .filter(models.TaskDB.scheduler_id == scheduler_id)
                .order_by(models.TaskDB.priority.asc())
                .order_by(models.TaskDB.created_at.asc())
                .offset(index)
                .first()
            )

            if item_orm is None:
                return None

            return models.Task.model_validate(item_orm)

    @retry()
    def update(self, scheduler_id: str, item: models.Task) -> None:
        with self.dbconn.session.begin() as session:
            (
                session.query(models.TaskDB)
                .filter(models.TaskDB.status == models.TaskStatus.QUEUED)
                .filter(models.TaskDB.scheduler_id == scheduler_id)
                .filter(models.TaskDB.id == item.id)
                .update(item.model_dump())
            )

    @retry()
    def remove(self, scheduler_id: str, item_id: UUID) -> None:
        with self.dbconn.session.begin() as session:
            (
                session.query(models.TaskDB)
                .filter(models.TaskDB.status == models.TaskStatus.QUEUED)
                .filter(models.TaskDB.scheduler_id == scheduler_id)
                .filter(models.TaskDB.id == str(item_id))
                .delete()
            )

    @retry()
    def get(self, scheduler_id, item_id: UUID) -> models.Task | None:
        with self.dbconn.session.begin() as session:
            item_orm = (
                session.query(models.TaskDB)
                .filter(models.TaskDB.status == models.TaskStatus.QUEUED)
                .filter(models.TaskDB.scheduler_id == scheduler_id)
                .filter(models.TaskDB.id == str(item_id))
                .first()
            )

            if item_orm is None:
                return None

            return models.Task.model_validate(item_orm)

    @retry()
    def empty(self, scheduler_id: str) -> bool:
        with self.dbconn.session.begin() as session:
            count = (
                session.query(models.TaskDB)
                .filter(models.TaskDB.status == models.TaskStatus.QUEUED)
                .filter(models.TaskDB.scheduler_id == scheduler_id)
                .count()
            )
            return count == 0

    @retry()
    def qsize(self, scheduler_id: str) -> int:
        with self.dbconn.session.begin() as session:
            count = (
                session.query(models.TaskDB)
                .filter(models.TaskDB.status == models.TaskStatus.QUEUED)
                .filter(models.TaskDB.scheduler_id == scheduler_id)
                .count()
            )

            return count

    @retry()
    def get_items(
        self,
        scheduler_id: str,
        filters: FilterRequest | None,
    ) -> tuple[list[models.Task], int]:
        with self.dbconn.session.begin() as session:
            query = (
                session.query(models.TaskDB)
                .filter(models.TaskDB.status == models.TaskStatus.QUEUED)
                .filter(models.TaskDB.scheduler_id == scheduler_id)
            )

            if filters is not None:
                query = apply_filter(models.TaskDB, query, filters)

            count = query.count()
            items_orm = query.all()

            return ([models.Task.model_validate(item_orm) for item_orm in items_orm], count)

    @retry()
    def get_item_by_hash(self, scheduler_id: str, item_hash: str) -> models.Task | None:
        with self.dbconn.session.begin() as session:
            item_orm = (
                session.query(models.TaskDB)
                .filter(models.TaskDB.status == models.TaskStatus.QUEUED)
                .order_by(models.TaskDB.created_at.desc())
                .filter(models.TaskDB.scheduler_id == scheduler_id)
                .filter(models.TaskDB.hash == item_hash)
                .first()
            )

            if item_orm is None:
                return None

            return models.Task.model_validate(item_orm)

    @retry()
    def get_items_by_scheduler_id(self, scheduler_id: str) -> list[models.Task]:
        with self.dbconn.session.begin() as session:
            items_orm = (
                session.query(models.TaskDB)
                .filter(models.TaskDB.status == models.TaskStatus.QUEUED)
                .filter(models.TaskDB.scheduler_id == scheduler_id)
                .all()
            )

            return [models.Task.model_validate(item_orm) for item_orm in items_orm]

    @retry()
    def clear(self, scheduler_id: str) -> None:
        with self.dbconn.session.begin() as session:
            (
                session.query(models.TaskDB)
                .filter(models.TaskDB.status == models.TaskStatus.QUEUED)
                .filter(models.TaskDB.scheduler_id == scheduler_id)
                .delete(),
            )
