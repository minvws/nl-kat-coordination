from datetime import datetime, timedelta, timezone

from sqlalchemy import exc, func

from scheduler import models

from .filters import FilterRequest, apply_filter
from .storage import DBConn, retry


class RunStore:
    name: str = "run_store"

    def __init__(self, dbconn: DBConn) -> None:
        self.dbconn = dbconn

    @retry()
    def get_runs(
        self,
        scheduler_id: str | None = None,
        task_type: str | None = None,
        status: str | None = None,
        min_created_at: datetime | None = None,
        max_created_at: datetime | None = None,
        filters: FilterRequest | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[models.TaskRun], int]:
        with self.dbconn.session.begin() as session:
            query = session.query(models.TaskRunDB)

            if scheduler_id is not None:
                query = query.filter(models.TaskRunDB.scheduler_id == scheduler_id)

            if task_type is not None:
                query = query.filter(models.TaskRunDB.type == task_type)

            if status is not None:
                query = query.filter(models.TaskRunDB.status == models.TaskStatus(status).name)

            if min_created_at is not None:
                query = query.filter(models.TaskRunDB.created_at >= min_created_at)

            if max_created_at is not None:
                query = query.filter(models.TaskRunDB.created_at <= max_created_at)

            if filters is not None:
                query = apply_filter(models.TaskRunDB, query, filters)

            try:
                count = query.count()
                tasks_orm = query.order_by(models.TaskRunDB.created_at.desc()).offset(offset).limit(limit).all()
            except exc.ProgrammingError as e:
                raise ValueError(f"Invalid filter: {e}") from e

            tasks = [models.TaskRun.model_validate(task_orm) for task_orm in tasks_orm]

            return tasks, count

    @retry()
    def get_runs_by_id(self, task_id: str) -> models.TaskRun | None:
        with self.dbconn.session.begin() as session:
            task_orm = session.query(models.TaskRunDB).filter(models.TaskRunDB.id == task_id).first()
            if task_orm is None:
                return None

            task = models.TaskRun.model_validate(task_orm)

            return task

    @retry()
    def get_runs_by_hash(self, task_hash: str) -> list[models.TaskRun] | None:
        with self.dbconn.session.begin() as session:
            tasks_orm = (
                session.query(models.TaskRunDB)
                .filter(models.TaskRunDB.p_item["hash"].as_string() == task_hash)
                .order_by(models.TaskRunDB.created_at.desc())
                .all()
            )

            if tasks_orm is None:
                return None

            tasks = [models.TaskRun.model_validate(task_orm) for task_orm in tasks_orm]

            return tasks

    @retry()
    def get_latest_run_by_hash(self, task_hash: str) -> models.TaskRun | None:
        with self.dbconn.session.begin() as session:
            task_orm = (
                session.query(models.TaskRunDB)
                .filter(models.TaskRunDB.p_item["hash"].as_string() == task_hash)
                .order_by(models.TaskRunDB.created_at.desc())
                .first()
            )

            if task_orm is None:
                return None

            task = models.TaskRun.model_validate(task_orm)

            return task

    @retry()
    def create_run(self, task: models.TaskRun) -> models.TaskRun | None:
        with self.dbconn.session.begin() as session:
            task_orm = models.TaskRunDB(**task.model_dump())
            session.add(task_orm)

            created_task = models.TaskRun.model_validate(task_orm)

            return created_task

    @retry()
    def update_run(self, task: models.TaskRun) -> None:
        with self.dbconn.session.begin() as session:
            (session.query(models.TaskRunDB).filter(models.TaskRunDB.id == task.id).update(task.model_dump()))

    @retry()
    def cancel_runs(self, scheduler_id: str, task_ids: list[str]) -> None:
        with self.dbconn.session.begin() as session:
            session.query(models.TaskRunDB).filter(
                models.TaskRunDB.scheduler_id == scheduler_id, models.TaskRunDB.id.in_(task_ids)
            ).update({"status": models.TaskStatus.CANCELLED.name})

    @retry()
    def get_status_count_per_hour(
        self,
        scheduler_id: str | None = None,
    ) -> dict[str, dict[str, int]] | None:
        with self.dbconn.session.begin() as session:
            query = (
                session.query(
                    func.DATE_TRUNC("hour", models.TaskRunDB.modified_at).label("hour"),
                    models.TaskRunDB.status,
                    func.count(models.TaskRunDB.id).label("count"),
                )
                .filter(
                    models.TaskRunDB.modified_at >= datetime.now(timezone.utc) - timedelta(hours=24),
                )
                .group_by("hour", models.TaskRunDB.status)
                .order_by("hour", models.TaskRunDB.status)
            )

            if scheduler_id is not None:
                query = query.filter(models.TaskRunDB.scheduler_id == scheduler_id)

            results = query.all()

            response: dict[str, dict[str, int]] = {}
            for row in results:
                date, status, task_count = row
                response.setdefault(date.isoformat(), {k.value: 0 for k in models.TaskStatus}).update(
                    {status.value: task_count}
                )
                response[date.isoformat()].update({"total": response[date.isoformat()].get("total", 0) + task_count})

            return response

    @retry()
    def get_status_counts(self, scheduler_id: str | None = None) -> dict[str, int] | None:
        with self.dbconn.session.begin() as session:
            query = (
                session.query(models.TaskRunDB.status, func.count(models.TaskRunDB.id).label("count"))
                .group_by(models.TaskRunDB.status)
                .order_by(models.TaskRunDB.status)
            )

            if scheduler_id is not None:
                query = query.filter(models.TaskRunDB.scheduler_id == scheduler_id)

            results = query.all()

            response = {k.value: 0 for k in models.TaskStatus}
            for row in results:
                status, task_count = row
                response[status.value] = task_count

            return response
