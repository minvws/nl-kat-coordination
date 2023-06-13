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
        filters: Optional[List[models.Filter]] = None,
    ) -> Tuple[List[models.Job], int]:
        with self.datastore.session.begin() as session:
            query = session.query(models.PrioritizedItemORM).filter(models.JobORM.scheduler_id == scheduler_id)

            if filters is not None:
                for f in filters:
                    query.filter(models.JobORM.data[f.get_field()].astext == f.value)

            count = query.count()
            jobs_orm = query.all()

            return ([models.Job.from_orm(job_orm) for job_orm in jobs_orm], count)

    @retry()
    def get_job(self, job_id: str) -> Optional[models.Job]:
        with self.datastore.session.begin() as session:
            job_orm = session.query(models.JobORM).filter(models.JobORM.id == job_id).first()

            if job_orm is None:
                return None

            return models.Job.from_orm(job_orm)

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
            job_orm = models.JobORM.from_orm(job)
            session.add(job_orm)
            session.flush()

            return models.Job.from_orm(job_orm)

    @retry()
    def update_job(self, job: models.Job) -> None:
        with self.datastore.session.begin() as session:
            session.query(models.JobORM).filter(models.JobORM.id == job.id).update(job.dict())
            """
            job_orm = session.query(models.JobORM).filter(models.JobORM.id == job.id).first()
            job_orm = models.JobORM.from_orm(job)
            session.add(job_orm)
            session.flush()

            return models.Job.from_orm(job_orm)
            """
