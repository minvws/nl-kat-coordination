from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func

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
        min_created_at: Optional[datetime] = None,
        max_created_at: Optional[datetime] = None,
        filters: Optional[List[models.Filter]] = None,
    ) -> Tuple[List[models.Task], int]:
        with self.dbconn.session.begin() as session:
            query = session.query(models.TaskDB).filter(
                models.TaskDB.scheduler_id == scheduler_id,
            )

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

            if filters is not None:
                for f in filters:
                    query.filter(models.TaskDB.p_item[f.get_field()].astext == f.value)

            count = query.count()
            tasks_orm = query.all()

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

    @retry()
    def api_list_tasks(
        self,
        scheduler_id: Optional[str],
        task_type: Optional[str],
        status: Optional[str],
        min_created_at: Optional[datetime],
        max_created_at: Optional[datetime],
        input_ooi: Optional[str],
        plugin_id: Optional[str],
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

            if input_ooi is not None:
                if type == "boefje":
                    query = query.filter(models.TaskDB.p_item[["data", "input_ooi"]].as_string() == input_ooi)
                elif type == "normalizer":
                    query = query.filter(
                        models.TaskDB.p_item[["data", "raw_data", "boefje_meta", "input_ooi"]].as_string() == input_ooi
                    )
                else:
                    query = query.filter(
                        (models.TaskDB.p_item[["data", "input_ooi"]].as_string() == input_ooi)
                        | (
                            models.TaskDB.p_item[["data", "raw_data", "boefje_meta", "input_ooi"]].as_string()
                            == input_ooi
                        )
                    )

            if plugin_id is not None:
                if type == "boefje":
                    query = query.filter(models.TaskDB.p_item[["data", "boefje", "id"]].as_string() == plugin_id)
                elif type == "normalizer":
                    query = query.filter(models.TaskDB.p_item[["data", "normalizer", "id"]].as_string() == plugin_id)
                else:
                    query = query.filter(
                        (models.TaskDB.p_item[["data", "boefje", "id"]].as_string() == plugin_id)
                        | (models.TaskDB.p_item[["data", "normalizer", "id"]].as_string() == plugin_id)
                    )

            count = query.count()

            tasks_orm = query.order_by(models.TaskDB.created_at.desc()).offset(offset).limit(limit).all()

            tasks = [models.Task.model_validate(task_orm) for task_orm in tasks_orm]

            return tasks, count

    @retry()
    def get_status_count_per_hour(
        self,
        scheduler_id: Optional[str] = None,
    ) -> Optional[Dict[str, Dict[str, int]]]:
        with self.dbconn.session.begin() as session:
            query = (
                session.query(
                    func.DATE_TRUNC("hour", models.TaskDB.modified_at).label("hour"),
                    models.TaskDB.status,
                    func.count(models.TaskDB.id).label("count"),
                )
                .filter(
                    models.TaskDB.modified_at >= datetime.now(timezone.utc) - timedelta(hours=24),
                )
                .group_by("hour", models.TaskDB.status)
                .order_by("hour", models.TaskDB.status)
            )

            if scheduler_id is not None:
                query = query.filter(models.TaskDB.scheduler_id == scheduler_id)

            results = query.all()

            response: Dict[str, Dict[str, int]] = {}
            for row in results:
                date, status, task_count = row
                response.setdefault(date.isoformat(), {k.value: 0 for k in models.TaskStatus}).update(
                    {status.value: task_count}
                )
                response[date.isoformat()].update({"total": response[date.isoformat()].get("total", 0) + task_count})

            return response

    @retry()
    def get_status_counts(self, scheduler_id: Optional[str] = None) -> Optional[Dict[str, int]]:
        with self.dbconn.session.begin() as session:
            query = (
                session.query(models.TaskDB.status, func.count(models.TaskDB.id).label("count"))
                .group_by(models.TaskDB.status)
                .order_by(models.TaskDB.status)
            )

            if scheduler_id is not None:
                query = query.filter(models.TaskDB.scheduler_id == scheduler_id)

            results = query.all()

            response = {k.value: 0 for k in models.TaskStatus}
            for row in results:
                status, task_count = row
                response[status.value] = task_count

            return response
