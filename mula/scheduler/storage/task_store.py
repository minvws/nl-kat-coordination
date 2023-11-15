from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy import exc, func

from scheduler.models import Task, TaskDB, TaskEventDB, TaskStatus

from .filters import FilterRequest, apply_filter
from .storage import DBConn, retry


class TaskStore:
    name: str = "task_store"

    def __init__(self, dbconn: DBConn) -> None:
        self.dbconn = dbconn

    @retry()
    def get_tasks(
        self,
        scheduler_id: Optional[str] = None,
        task_type: Optional[str] = None,
        status: Optional[str] = None,
        min_created_at: Optional[datetime] = None,
        max_created_at: Optional[datetime] = None,
        filters: Optional[FilterRequest] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Task], int]:
        with self.dbconn.session.begin() as session:
            query = session.query(TaskDB)

            if scheduler_id is not None:
                query = query.filter(TaskDB.scheduler_id == scheduler_id)

            if task_type is not None:
                query = query.filter(TaskDB.type == task_type)

            if status is not None:
                query = query.filter(TaskDB.status == TaskStatus(status).name)

            if min_created_at is not None:
                query = query.filter(TaskDB.created_at >= min_created_at)

            if max_created_at is not None:
                query = query.filter(TaskDB.created_at <= max_created_at)

            if filters is not None:
                query = apply_filter(TaskDB, query, filters)

            try:
                count = query.count()
                tasks_orm = query.order_by(TaskDB.created_at.desc()).offset(offset).limit(limit).all()
            except exc.ProgrammingError as e:
                raise ValueError(f"Invalid filter: {e}") from e

            tasks = [Task.model_validate(task_orm) for task_orm in tasks_orm]

            return tasks, count

    @retry()
    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        with self.dbconn.session.begin() as session:
            task_orm = session.query(TaskDB).filter(TaskDB.id == task_id).first()
            if task_orm is None:
                return None

            task = Task.model_validate(task_orm)

            return task

    @retry()
    def get_tasks_by_hash(self, task_hash: str) -> Optional[List[Task]]:
        with self.dbconn.session.begin() as session:
            tasks_orm = (
                session.query(TaskDB)
                .filter(TaskDB.p_item["hash"].as_string() == task_hash)
                .order_by(TaskDB.created_at.desc())
                .all()
            )

            if tasks_orm is None:
                return None

            tasks = [Task.model_validate(task_orm) for task_orm in tasks_orm]

            return tasks

    @retry()
    def get_latest_task_by_hash(self, task_hash: str) -> Optional[Task]:
        with self.dbconn.session.begin() as session:
            task_orm = (
                session.query(TaskDB)
                .filter(TaskDB.p_item["hash"].as_string() == task_hash)
                .order_by(TaskDB.created_at.desc())
                .first()
            )

            if task_orm is None:
                return None

            task = Task.model_validate(task_orm)

            return task

    @retry()
    def create_task(self, task: Task) -> Optional[Task]:
        with self.dbconn.session.begin() as session:
            task_orm = TaskDB(**task.model_dump())
            session.add(task_orm)

            created_task = Task.model_validate(task_orm)

            return created_task

    @retry()
    def update_task(self, task: Task) -> None:
        with self.dbconn.session.begin() as session:
            (session.query(TaskDB).filter(TaskDB.id == task.id).update(task.model_dump()))

    @retry()
    def cancel_tasks(self, scheduler_id: str, task_ids: List[str]) -> None:
        with self.dbconn.session.begin() as session:
            session.query(TaskDB).filter(
                TaskDB.scheduler_id == scheduler_id, TaskDB.id.in_(task_ids)
            ).update({"status": TaskStatus.CANCELLED.name})

    @retry()
    def get_status_count_per_hour(
        self,
        scheduler_id: Optional[str] = None,
    ) -> Optional[Dict[str, Dict[str, int]]]:
        with self.dbconn.session.begin() as session:
            query = (
                session.query(
                    func.DATE_TRUNC("hour", TaskDB.modified_at).label("hour"),
                    TaskDB.status,
                    func.count(TaskDB.id).label("count"),
                )
                .filter(
                    TaskDB.modified_at >= datetime.now(timezone.utc) - timedelta(hours=24),
                )
                .group_by("hour", TaskDB.status)
                .order_by("hour", TaskDB.status)
            )

            if scheduler_id is not None:
                query = query.filter(TaskDB.scheduler_id == scheduler_id)

            results = query.all()

            response: Dict[str, Dict[str, int]] = {}
            for row in results:
                date, status, task_count = row
                response.setdefault(date.isoformat(), {k.value: 0 for k in TaskStatus}).update(
                    {status.value: task_count}
                )
                response[date.isoformat()].update({"total": response[date.isoformat()].get("total", 0) + task_count})

            return response

    @retry()
    def get_status_counts(self, scheduler_id: Optional[str] = None) -> Optional[Dict[str, int]]:
        with self.dbconn.session.begin() as session:
            query = (
                session.query(TaskDB.status, func.count(TaskDB.id).label("count"))
                .group_by(TaskDB.status)
                .order_by(TaskDB.status)
            )

            if scheduler_id is not None:
                query = query.filter(TaskDB.scheduler_id == scheduler_id)

            results = query.all()

            response = {k.value: 0 for k in TaskStatus}
            for row in results:
                status, task_count = row
                response[status.value] = task_count

            return response

    @retry()
    def get_task_duration(self, task_id: str) -> float:
        start_time: Optional[datetime] = None
        end_time: Optional[datetime] = None

        with self.dbconn.session.begin() as session:
            query = (
                session.query(TaskEventDB.task_id == task_id)
                .filter(TaskEventDB.type == "events.db")
                .filter(TaskEventDB.context == "task")
                .filter(TaskEventDB.event == "insert")
                .filter(TaskEventDB.data["status"] == TaskStatus.QUEUED)
                .order_by(TaskEventDB.datetime.asc())
            )

            result_start = query.first()
            if result_start is not None:
                start_time = result_start.datetime

            # Get task event end time when status is completed or failed
            query = (
                session.query(TaskEventDB.task_id == task_id)
                .filter(TaskEventDB.type == "events.db")
                .filter(TaskEventDB.context == "task")
                .filter(TaskEventDB.event == "update")
                .filter(TaskEventDB.data["status"].in_([TaskStatus.COMPLETED, TaskStatus.FAILED]))
                .order_by(TaskEventDB.datetime.desc())
            )

            result_end = query.first()
            if result_end is not None:
                end_time = result_end.datetime

        if start_time is not None and end_time is not None:
            return (end_time - start_time).total_seconds()

        return 0

    @retry()
    def get_task_runtime(self, task_id: str) -> float:
        start_time: Optional[datetime] = None
        end_time: Optional[datetime] = None

        with self.dbconn.session.begin() as session:
            query = (
                session.query(TaskEventDB.task_id == task_id)
                .filter(TaskEventDB.type == "events.db")
                .filter(TaskEventDB.context == "task")
                .filter(TaskEventDB.event == "update")
                .filter(TaskEventDB.data["status"] == TaskStatus.DISPATCHED)
                .order_by(TaskEventDB.datetime.asc())
            )

            result_start = query.first()
            if result_start is not None:
                start_time = result_start.datetime

            # Get task event end time when status is completed or failed
            query = (
                session.query(TaskEventDB.task_id == task_id)
                .filter(TaskEventDB.type == "events.db")
                .filter(TaskEventDB.context == "task")
                .filter(TaskEventDB.event == "update")
                .filter(TaskEventDB.data["status"].in_([TaskStatus.COMPLETED, TaskStatus.FAILED]))
                .order_by(TaskEventDB.datetime.desc())
            )

            result_end = query.first()
            if result_end is not None:
                end_time = result_end.datetime

        if start_time is not None and end_time is not None:
            return (end_time - start_time).total_seconds()

        return 0

    @retry()
    def get_task_queued(self, task_id: str) -> float:
        start_time: Optional[datetime] = None
        end_time: Optional[datetime] = None

        with self.dbconn.session.begin() as session:
            query = (
                session.query(TaskEventDB.task_id == task_id)
                .filter(TaskEventDB.type == "events.db")
                .filter(TaskEventDB.context == "task")
                .filter(TaskEventDB.event == "insert")
                .filter(TaskEventDB.data["status"] == TaskStatus.QUEUED)
                .order_by(TaskEventDB.datetime.asc())
            )

            result_start = query.first()
            if result_start is not None:
                start_time = result_start.datetime

            # Get task event end time when status is completed or failed
            query = (
                session.query(TaskEventDB.task_id == task_id)
                .filter(TaskEventDB.type == "events.db")
                .filter(TaskEventDB.context == "task")
                .filter(TaskEventDB.event == "update")
                .filter(TaskEventDB.data["status"] == TaskStatus.DISPATCHED)
                .order_by(TaskEventDB.datetime.desc())
            )

            result_end = query.first()
            if result_end is not None:
                end_time = result_end.datetime

        if start_time is not None and end_time is not None:
            return (end_time - start_time).total_seconds()

        return 0
