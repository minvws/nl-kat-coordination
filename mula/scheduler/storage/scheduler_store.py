from datetime import datetime, timedelta, timezone

from sqlalchemy import exc, func

from scheduler import models

from .errors import StorageError, exception_handler
from .filters import FilterRequest, apply_filter
from .storage import DBConn
from .utils import retry


class SchedulerStore:
    name: str = "scheduler_store"

    def __init__(self, dbconn: DBConn) -> None:
        self.dbconn = dbconn

    @retry()
    @exception_handler
    def get_schedulers(
        self,
        scheduler_id: str | None = None,
        item_type: str | None = None,
        min_created_at: datetime | None = None,
        max_created_at: datetime | None = None,
        min_modified_at: datetime | None = None,
        max_modified_at: datetime | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[models.Scheduler], int]:
        with self.dbconn.session.begin() as session:
            query = session.query(models.SchedulerDB)

            if scheduler_id is not None:
                query = query.filter(models.SchedulerDB.id == scheduler_id)

            if item_type is not None:
                query = query.filter(models.SchedulerDB.item_type == item_type)

            if min_created_at is not None:
                query = query.filter(models.SchedulerDB.created_at >= min_created_at)

            if max_created_at is not None:
                query = query.filter(models.SchedulerDB.created_at <= max_created_at)

            if min_modified_at is not None:
                query = query.filter(models.SchedulerDB.modified_at >= min_modified_at)

            if max_modified_at is not None:
                query = query.filter(models.SchedulerDB.modified_at <= max_modified_at)

            try:
                count = query.count()
                schedulers_orm = query.order_by(models.SchedulerDB.created_at.desc()).offset(offset).limit(limit).all()
            except exc.ProgrammingError as e:
                raise StorageError(f"Invalid filter: {e}") from e

            schedulers = [models.Scheduler.model_validate(scheduler_orm) for scheduler_orm in schedulers_orm]

            return schedulers, count
