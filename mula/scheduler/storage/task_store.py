import datetime
from typing import List, Optional, Tuple

from scheduler import models

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
        filters: Optional[List[models.Filter]] = None,
    ) -> Tuple[List[models.Task], int]:
        with self.dbconn.session.begin() as session:
            query = session.query(models.TaskORM).filter(
                models.TaskORM.scheduler_id == scheduler_id,
            )

            if scheduler_id is not None:
                query = query.filter(models.TaskORM.scheduler_id == scheduler_id)

            if task_type is not None:
                query = query.filter(models.TaskORM.type == task_type)

            if status is not None:
                query = query.filter(models.TaskORM.status == models.TaskStatus(status).name)

            if min_created_at is not None:
                query = query.filter(models.TaskORM.created_at >= min_created_at)

            if max_created_at is not None:
                query = query.filter(models.TaskORM.created_at <= max_created_at)

            if filters is not None:
                for f in filters:
                    query.filter(models.TaskORM.p_item[f.get_field()].astext == f.value)

            count = query.count()
            tasks_orm = query.all()

            tasks = [models.Task.from_orm(task_orm) for task_orm in tasks_orm]

            return tasks, count

    @retry()
    def get_task_by_id(self, task_id: str) -> Optional[models.Task]:
        with self.dbconn.session.begin() as session:
            task_orm = session.query(models.TaskORM).filter(models.TaskORM.id == task_id).first()
            if task_orm is None:
                return None

            task = models.Task.from_orm(task_orm)

            return task

    @retry()
    def get_tasks_by_hash(self, task_hash: str) -> Optional[List[models.Task]]:
        with self.dbconn.session.begin() as session:
            tasks_orm = (
                session.query(models.TaskORM)
                .filter(models.TaskORM.p_item["hash"].as_string() == task_hash)
                .order_by(models.TaskORM.created_at.desc())
                .all()
            )

            if tasks_orm is None:
                return None

            tasks = [models.Task.from_orm(task_orm) for task_orm in tasks_orm]

            return tasks

    @retry()
    def get_latest_task_by_hash(self, task_hash: str) -> Optional[models.Task]:
        with self.dbconn.session.begin() as session:
            task_orm = (
                session.query(models.TaskORM)
                .filter(models.TaskORM.p_item["hash"].as_string() == task_hash)
                .order_by(models.TaskORM.created_at.desc())
                .first()
            )

            if task_orm is None:
                return None

            task = models.Task.from_orm(task_orm)

            return task

    @retry()
    def create_task(self, task: models.Task) -> Optional[models.Task]:
        with self.dbconn.session.begin() as session:
            task_orm = models.TaskORM(**task.dict())
            session.add(task_orm)

            created_task = models.Task.from_orm(task_orm)

            return created_task

    @retry()
    def update_task(self, task: models.Task) -> None:
        with self.dbconn.session.begin() as session:
            (session.query(models.TaskORM).filter(models.TaskORM.id == task.id).update(task.dict()))

    @retry()
    def cancel_tasks(self, scheduler_id: str, task_ids: List[str]) -> None:
        with self.dbconn.session.begin() as session:
            session.query(models.TaskORM).filter(
                models.TaskORM.scheduler_id == scheduler_id, models.TaskORM.id.in_(task_ids)
            ).update({"status": models.TaskStatus.CANCELLED.name})

    @retry()
    def api_list_tasks(
        self,
        scheduler_id: Optional[str],
        task_type: Optional[str],
        status: Optional[str],
        min_created_at: Optional[datetime.datetime],
        max_created_at: Optional[datetime.datetime],
        input_ooi: Optional[str],
        plugin_id: Optional[str],
        offset: int = 0,
        limit: int = 100,
    ) -> Tuple[List[models.Task], int]:
        with self.dbconn.session.begin() as session:
            query = session.query(models.TaskORM)

            if scheduler_id is not None:
                query = query.filter(models.TaskORM.scheduler_id == scheduler_id)

            if task_type is not None:
                query = query.filter(models.TaskORM.type == task_type)

            if status is not None:
                query = query.filter(models.TaskORM.status == models.TaskStatus(status).name)

            if min_created_at is not None:
                query = query.filter(models.TaskORM.created_at >= min_created_at)

            if max_created_at is not None:
                query = query.filter(models.TaskORM.created_at <= max_created_at)

            if input_ooi is not None:
                if type == "boefje":
                    query = query.filter(models.TaskORM.p_item[["data", "input_ooi"]].as_string() == input_ooi)
                elif type == "normalizer":
                    query = query.filter(
                        models.TaskORM.p_item[["data", "raw_data", "boefje_meta", "input_ooi"]].as_string() == input_ooi
                    )
                else:
                    query = query.filter(
                        (models.TaskORM.p_item[["data", "input_ooi"]].as_string() == input_ooi)
                        | (
                            models.TaskORM.p_item[["data", "raw_data", "boefje_meta", "input_ooi"]].as_string()
                            == input_ooi
                        )
                    )

            if plugin_id is not None:
                if type == "boefje":
                    query = query.filter(models.TaskORM.p_item[["data", "boefje", "id"]].as_string() == plugin_id)
                elif type == "normalizer":
                    query = query.filter(models.TaskORM.p_item[["data", "normalizer", "id"]].as_string() == plugin_id)
                else:
                    query = query.filter(
                        (models.TaskORM.p_item[["data", "boefje", "id"]].as_string() == plugin_id)
                        | (models.TaskORM.p_item[["data", "normalizer", "id"]].as_string() == plugin_id)
                    )

            count = query.count()

            tasks_orm = query.order_by(models.TaskORM.created_at.desc()).offset(offset).limit(limit).all()

            tasks = [models.Task.from_orm(task_orm) for task_orm in tasks_orm]

            return tasks, count
