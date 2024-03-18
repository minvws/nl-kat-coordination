from sqlalchemy import exc, func

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
        task_id: str | None = None,
        task_hash: str | None = None,
        filters: FilterRequest | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[models.Task], int]:
        with self.dbconn.session.begin() as session:
            query = session.query(models.TaskDB)

            if task_id is not None:
                query = query.filter(models.TaskDB.id == task_id)

            if task_hash is not None:
                query = query.filter(models.TaskDB.hash == task_hash)

            if filters is not None:
                query = apply_filter(models.TaskDB, query, filters)

            try:
                count = query.count()
                tasks_orm = query.order_by(models.TaskDB.created_at.desc()).offset(offset).limit(limit).all()
            except exc.ProgrammingError as e:
                raise ValueError(f"Invalid filter: {e}") from e

            tasks = [models.Task.model_validate(task_orm) for task_orm in tasks_orm]

            return tasks, count

    @retry()
    def get_task(self, task_id: str) -> models.Task:
        with self.dbconn.session.begin() as session:
            task_orm = session.query(models.TaskDB).filter(models.TaskDB.id == task_id).one_or_none()

            if task_orm is None:
                raise ValueError(f"Task not found: {task_id}")

            return models.Task.model_validate(task_orm)

    @retry()
    def create_task(self, task: models.Task) -> models.Task:
        with self.dbconn.session.begin() as session:
            task_orm = models.TaskDB(**task.model_dump())
            session.add(task_orm)

            created_task = models.Task.model_validate(task_orm)

            return created_task

    @retry()
    def update_task(self, task: models.Task) -> models.Task:
        with self.dbconn.session.begin() as session:
            task_orm = session.query(models.TaskDB).filter(models.TaskDB.id == task.id).one_or_none()

            if task_orm is None:
                raise ValueError(f"Task not found: {task.id}")

            task_orm.update(task.model_dump())
            session.add(task_orm)

            # TODO: validate cron expression
            updated_task = models.Task.model_validate(task_orm)

            return updated_task
