import datetime
from typing import List, Optional, Tuple

from scheduler import models

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
        min_created_at: Optional[datetime.datetime] = None,
        max_created_at: Optional[datetime.datetime] = None,
        filter_request: Optional[FilterRequest] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Tuple[List[models.Task], int]:
        with self.dbconn.session.begin() as session:
            query = session.query(models.TaskDB)

            if scheduler_id is not None:
                query = query.filter(models.TaskDB.scheduler_id == scheduler_id)

            if task_type is not None:
                query = query.filter(models.TaskDB.type == task_type)

            if status is not None:
                query = query.filter(models.TaskDB.status == models.TaskStatus(status).name)

            if min_created_at is not None:
                query = query.filter(models.TaskDB.created_at >= min_created_at)

            if max_created_at is not None:
                query = query.filter(models.TaskDB.created_at <= max_created_at)

            if filter_request is not None:
                query = apply_filter(models.TaskDB, query, filter_request)


            count = query.count()
            tasks_orm = query.order_by(models.TaskDB.created_at.desc()).offset(offset).limit(limit).all()

            tasks = [models.Task.model_validate(task_orm) for task_orm in tasks_orm]

            return tasks, count

    @retry()
    def get_task_by_id(self, task_id: str) -> Optional[models.Task]:
        with self.dbconn.session.begin() as session:
            task_orm = session.query(models.TaskDB).filter(models.TaskDB.id == task_id).first()
            if task_orm is None:
                return None

            task = models.Task.model_validate(task_orm)

            return task

    @retry()
    def get_tasks_by_hash(self, task_hash: str) -> Optional[List[models.Task]]:
        with self.dbconn.session.begin() as session:
            tasks_orm = (
                session.query(models.TaskDB)
                .filter(models.TaskDB.p_item["hash"].as_string() == task_hash)
                .order_by(models.TaskDB.created_at.desc())
                .all()
            )

            if tasks_orm is None:
                return None

            tasks = [models.Task.model_validate(task_orm) for task_orm in tasks_orm]

            return tasks

    @retry()
    def get_latest_task_by_hash(self, task_hash: str) -> Optional[models.Task]:
        with self.dbconn.session.begin() as session:
            task_orm = (
                session.query(models.TaskDB)
                .filter(models.TaskDB.p_item["hash"].as_string() == task_hash)
                .order_by(models.TaskDB.created_at.desc())
                .first()
            )

            if task_orm is None:
                return None

            task = models.Task.model_validate(task_orm)

            return task

    @retry()
    def create_task(self, task: models.Task) -> Optional[models.Task]:
        with self.dbconn.session.begin() as session:
            task_orm = models.TaskDB(**task.model_dump())
            session.add(task_orm)

            created_task = models.Task.model_validate(task_orm)

            return created_task

    @retry()
    def update_task(self, task: models.Task) -> None:
        with self.dbconn.session.begin() as session:
            (session.query(models.TaskDB).filter(models.TaskDB.id == task.id).update(task.model_dump()))

    @retry()
    def cancel_tasks(self, scheduler_id: str, task_ids: List[str]) -> None:
        with self.dbconn.session.begin() as session:
            session.query(models.TaskDB).filter(
                models.TaskDB.scheduler_id == scheduler_id, models.TaskDB.id.in_(task_ids)
            ).update({"status": models.TaskStatus.CANCELLED.name})
