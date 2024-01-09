from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy import exc, func

from scheduler import models

from .filters import FilterRequest, apply_filter
from .storage import DBConn, retry


class JobStore:
    name: str = "job_store"

    def __init__(self, dbconn: DBConn) -> None:
        self.dbconn = dbconn

    @retry()
    def get_jobs(
        self,
        scheduler_id: str,
        enabled: Optional[bool] = None,
        min_deadline: Optional[datetime] = None,
        max_deadline: Optional[datetime] = None,
        filters: Optional[FilterRequest] = None,
        offset: Optional[int] = 0,
        limit: Optional[int] = 100,
    ) -> Tuple[List[models.Job], int]:
        with self.dbconn.session.begin() as session:
            query = session.query(models.JobDB)

            if scheduler_id is not None:
                query = query.filter(models.JobDB.scheduler_id == scheduler_id)

            if enabled is not None:
                query = query.filter(models.JobDB.enabled == enabled)

            if min_deadline is not None:
                query = query.filter(models.JobDB.deadline_at >= min_deadline)

            if max_deadline is not None:
                query = query.filter(models.JobDB.deadline_at <= max_deadline)

            if filters is not None:
                query = apply_filter(models.JobDB, query, filters)

            try:
                count = query.count()
                jobs_orm = query.order_by(models.JobDB.created_at.desc()).offset(offset).limit(limit).all()
            except exc.ProgrammingError as e:
                raise ValueError(f"Invalid filter: {e}") from e

            jobs = [models.Job.model_validate(job_orm) for job_orm in jobs_orm]

            return jobs, count

    @retry()
    def get_job_by_id(self, job_id: str) -> Optional[models.Job]:
        with self.dbconn.session.begin() as session:
            job_orm = session.query(models.JobDB).filter(models.JobDB.id == job_id).first()
            if job_orm is None:
                return None

            job = models.Job.model_validate(job_orm)

            return job

    @retry()
    def get_job_by_hash(self, hash: str) -> Optional[models.Job]:
        with self.dbconn.session.begin() as session:
            job_orm = session.query(models.JobDB).filter(models.JobDB.p_item["hash"].as_string() == hash).first()

            if job_orm is None:
                return None

            job = models.Job.model_validate(job_orm)

            return job

    @retry()
    def create_job(self, job: models.Job) -> Optional[models.Job]:
        with self.dbconn.session.begin() as session:
            job_orm = models.JobDB(**job.model_dump(exclude={"tasks"}))
            session.add(job_orm)

            created_job = models.Job.model_validate(job_orm)

            return created_job

    @retry()
    def update_job(self, job: models.Job) -> None:
        with self.dbconn.session.begin() as session:
            (session.query(models.JobDB).filter(models.JobDB.id == job.id).update(job.model_dump(exclude={"tasks"})))

    @retry()
    def update_job_enabled(self, job_id: str, enabled: bool) -> None:
        with self.dbconn.session.begin() as session:
            (session.query(models.JobDB).filter(models.JobDB.id == job_id).update({"enabled": enabled}))
