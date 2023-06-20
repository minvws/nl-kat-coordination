import datetime
from typing import List, Optional, Tuple

from scheduler import models

from ..stores import JobStorer  # noqa: TID252
from .datastore import SQLAlchemy, retry


class JobStore(JobStorer):
    def __init__(self, datastore: SQLAlchemy) -> None:
        super().__init__()

        self.datastore = datastore

    @retry()
    def get_jobs(
        self,
        scheduler_id: str,
        job_hash: Optional[str] = None,
        enabled: Optional[bool] = None,
        min_deadline: Optional[datetime.datetime] = None,
        max_deadline: Optional[datetime.datetime] = None,
        filters: Optional[List[models.Filter]] = None,
        offset: Optional[int] = 0,
        limit: Optional[int] = 100,
    ) -> Tuple[List[models.Job], int]:
        with self.datastore.session.begin() as session:
            query = session.query(models.PrioritizedItemORM)

            if scheduler_id is not None:
                query.filter(models.JobORM.scheduler_id == scheduler_id)

            if job_hash is not None:
                query.filter(models.JobORM.hash == job_hash)

            if enabled is not None:
                query.filter(models.JobORM.enabled == enabled)

            if min_deadline is not None:
                query.filter(models.JobORM.deadline >= min_deadline)

            if max_deadline is not None:
                query.filter(models.JobORM.deadline <= max_deadline)

            if filters is not None:
                for f in filters:
                    query.filter(models.JobORM.data[f.get_field()].astext == f.value)

            count = query.count()
            jobs_orm = query.offset(offset).limit(limit).all()

            jobs = [models.Job.from_orm(job_orm) for job_orm in jobs_orm]

            return jobs, count

    @retry()
    def get_job(self, job_id: str) -> Optional[models.Job]:
        with self.datastore.session.begin() as session:
            job_orm = session.query(models.JobORM).filter(models.JobORM.id == job_id).first()
            if job_orm is None:
                return None

            job = models.Job.from_orm(job_orm)

            return job

    @retry()
    def get_job_by_hash(self, job_hash: str) -> Optional[models.Job]:
        with self.datastore.session.begin() as session:
            job_orm = session.query(models.JobORM).filter(models.JobORM.hash == job_hash).first()

            if job_orm is None:
                return None

            return models.Job.from_orm(job_orm)

    @retry()
    def create_job(self, job: models.Job) -> models.Job:
        with self.datastore.session.begin() as session:
            job_orm = models.JobORM(**job.dict())
            session.add(job_orm)
            session.flush()

            return models.Job.from_orm(job_orm)

    @retry()
    def update_job(self, job: models.Job) -> None:
        with self.datastore.session.begin() as session:
            session.query(models.JobORM).filter(models.JobORM.id == job.id).update(job.dict())
