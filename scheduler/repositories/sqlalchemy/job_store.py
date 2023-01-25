import datetime
from typing import List, Optional, Tuple, Union

from scheduler import models

from ..stores import JobStorer
from .datastore import SQLAlchemy


# TODO: org id?
class JobStore(JobStorer):
    def __init__(self, datastore: SQLAlchemy) -> None:
        super().__init__()

        self.datastore = datastore

    def get_scheduled_jobs(
        self,
        scheduler_id: Optional[str],
        enabled: Optional[bool] = True,
        min_checked_at: Optional[datetime.datetime] = None,
        max_checked_at: Optional[datetime.datetime] = None,
    ) -> Tuple[List[models.ScheduledJob], int]:
        """Get all scheduled jobs.

        Returns:
            A list of ScheduledJob instances.
        """
        with self.datastore.session() as session:
            query = session.query(models.ScheduledJobORM)

            if scheduler_id is not None:
                query = query.filter(models.ScheduledJobORM.scheduler_id == scheduler_id)

            if enabled is not None:
                query = query.filter(models.ScheduledJobORM.enabled == enabled)

            if min_checked_at is not None:
                query = query.filter(models.ScheduledJobORM.checked_at >= min_checked_at)

            if max_checked_at is not None:
                query = query.filter(models.ScheduledJobORM.checked_at <= max_checked_at)

            count = query.count()

            jobs_orm = query.all()

            jobs = [models.ScheduledJob.from_orm(job_orm) for job_orm in jobs_orm]

            return jobs, count

    def get_scheduled_job(self, job_id: str) -> Optional[models.ScheduledJob]:
        """Get a scheduled job.

        Args:
            job_id: The ID of the job to get.

        Returns:
            The ScheduledJob instance if found, None otherwise.
        """
        with self.datastore.session() as session:
            job_orm = session.query(models.ScheduledJobORM).get(job_id)

            if job_orm is None:
                return None

            return models.ScheduledJob.from_orm(job_orm)

    def get_scheduled_job_by_hash(self, item_hash: str) -> Optional[models.ScheduledJob]:
        """Get a scheduled job by its hash.

        Args:
            hash: The hash of the job to get.

        Returns:
            The ScheduledJob instance if found, None otherwise.
        """
        with self.datastore.session() as session:
            job_orm = session.query(models.ScheduledJobORM).filter(models.ScheduledJobORM.hash == item_hash).first()

            if job_orm is None:
                return None

            job = models.ScheduledJob.from_orm(job_orm)

            return job

    def create_scheduled_job(self, job: models.ScheduledJob) -> Optional[models.ScheduledJob]:
        """Create a scheduled job.

        Args:
            scheduled_job: The scheduled job to create.
        """
        with self.datastore.session() as session:
            job_orm = models.ScheduledJobORM(**job.dict())
            session.add(job_orm)

            created_job = models.ScheduledJob.from_orm(job_orm)
            import pdb; pdb.set_trace()

            return created_job

    def update_scheduled_job(self, job: models.ScheduledJob) -> None:
        """Update a scheduled job.

        Args:
            scheduled_job: The scheduled job to update.
        """
        with self.datastore.session() as session:
            (session.query(models.ScheduledJobORM).filter(models.ScheduledJobORM.id == job.id).update(job.dict()))
