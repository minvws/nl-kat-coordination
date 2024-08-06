from uuid import UUID

from scheduler import models

from .errors import exception_handler
from .filters import FilterRequest, apply_filter
from .storage import DBConn
from .utils import retry


class PriorityQueueStore:
    name: str = "pq_store"

    def __init__(self, dbconn: DBConn) -> None:
        self.dbconn = dbconn

    @retry()
    @exception_handler
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
    @exception_handler
    def push(self, item: models.Task) -> models.Task | None:
        with self.dbconn.session.begin() as session:
            item_orm = models.TaskDB(**item.model_dump())
            session.add(item_orm)

            return models.Task.model_validate(item_orm)

    @retry()
    @exception_handler
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
    @exception_handler
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
    @exception_handler
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
    @exception_handler
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
    @exception_handler
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
    @exception_handler
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
    @exception_handler
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

            return (
                [models.Task.model_validate(item_orm) for item_orm in items_orm],
                count,
            )

    @retry()
    @exception_handler
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
    @exception_handler
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
    @exception_handler
    def clear(self, scheduler_id: str) -> None:
        with self.dbconn.session.begin() as session:
            (
                session.query(models.TaskDB)
                .filter(models.TaskDB.status == models.TaskStatus.QUEUED)
                .filter(models.TaskDB.scheduler_id == scheduler_id)
                .delete(),
            )
