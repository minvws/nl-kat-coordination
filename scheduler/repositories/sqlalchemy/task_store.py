from typing import List, Optional, Tuple, Union

from scheduler import models

from ..stores import TaskStorer
from .datastore import SQLAlchemy


class TaskStore(TaskStorer):
    """Datastore for Tasks.

    Attributes:
        datastore: SQAlchemy satastore to use for the database connection.
    """

    def __init__(self, datastore: SQLAlchemy) -> None:
        super().__init__()

        self.datastore = datastore

    def get_tasks(
        self, scheduler_id: Union[str, None], status: Union[str, None], offset: int = 0, limit: int = 100
    ) -> Tuple[List[models.Task], int]:
        with self.datastore.session.begin() as session:
            query = session.query(models.TaskORM)

            if scheduler_id is not None:
                query = query.filter(models.TaskORM.scheduler_id == scheduler_id)

            if status is not None:
                query = query.filter(models.TaskORM.status == models.TaskStatus(status).name)

            count = query.count()
            tasks_orm = query.order_by(models.TaskORM.created_at.desc()).offset(offset).limit(limit).all()

            tasks = [models.Task.from_orm(task_orm) for task_orm in tasks_orm]

            return tasks, count

    def get_task_by_id(self, task_id: str) -> Optional[models.Task]:
        with self.datastore.session.begin() as session:
            task_orm = session.query(models.TaskORM).filter(models.TaskORM.id == task_id).first()
            if task_orm is None:
                return None

            task = models.Task.from_orm(task_orm)

            return task

    def get_task_by_hash(self, task_hash: str) -> Optional[models.Task]:
        with self.datastore.session.begin() as session:
            task_orm = (
                session.query(models.TaskORM).filter(models.TaskORM.p_item["hash"].as_string() == task_hash).first()
            )

            if task_orm is None:
                return None

            task = models.Task.from_orm(task_orm)

            return task

    def create_task(self, task: models.Task) -> Optional[models.Task]:
        with self.datastore.session.begin() as session:
            task_orm = models.TaskORM(**task.dict())
            session.add(task_orm)

            created_task = models.Task.from_orm(task_orm)

            return created_task

    def update_task(self, task: models.Task) -> None:
        with self.datastore.session.begin() as session:
            (session.query(models.TaskORM).filter(models.TaskORM.id == task.id).update(task.dict()))
