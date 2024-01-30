from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import exc

from scheduler import models

from .filters import FilterRequest, apply_filter
from .storage import DBConn, retry


class ScheduleStore:
    name: str = "schedule_store"

    def __init__(self, dbconn: DBConn) -> None:
        self.dbconn = dbconn

    @retry()
    def get_schedules(
        self,
        scheduler_id: str,
        enabled: Optional[bool] = None,
        min_deadline: Optional[datetime] = None,
        max_deadline: Optional[datetime] = None,
        filters: Optional[FilterRequest] = None,
        offset: Optional[int] = 0,
        limit: Optional[int] = 100,
    ) -> Tuple[List[models.Schedule], int]:
        with self.dbconn.session.begin() as session:
            query = session.query(models.ScheduleDB)

            if scheduler_id is not None:
                query = query.filter(models.ScheduleDB.scheduler_id == scheduler_id)

            if enabled is not None:
                query = query.filter(models.ScheduleDB.enabled == enabled)

            if min_deadline is not None:
                query = query.filter(models.ScheduleDB.deadline_at >= min_deadline)

            if max_deadline is not None:
                query = query.filter(models.ScheduleDB.deadline_at <= max_deadline)

            if filters is not None:
                query = apply_filter(models.ScheduleDB, query, filters)

            try:
                count = query.count()
                schedules_orm = query.order_by(models.ScheduleDB.created_at.desc()).offset(offset).limit(limit).all()
            except exc.ProgrammingError as e:
                raise ValueError(f"Invalid filter: {e}") from e

            schedules = [models.Schedule.model_validate(schedule_orm) for schedule_orm in schedules_orm]

            return schedules, count

    @retry()
    def get_schedule_by_id(self, schedule_id: str) -> Optional[models.Schedule]:
        with self.dbconn.session.begin() as session:
            schedule_orm = session.query(models.ScheduleDB).filter(models.ScheduleDB.id == schedule_id).first()
            if schedule_orm is None:
                return None

            schedule = models.Schedule.model_validate(schedule_orm)

            return schedule

    @retry()
    def get_schedule_by_hash(self, schedule_hash: str) -> Optional[models.Schedule]:
        with self.dbconn.session.begin() as session:
            schedule_orm = (
                session.query(models.ScheduleDB)
                .filter(models.ScheduleDB.p_item["hash"].as_string() == schedule_hash)
                .first()
            )

            if schedule_orm is None:
                return None

            schedule = models.Schedule.model_validate(schedule_orm)

            return schedule

    @retry()
    def create_schedule(self, schedule: models.Schedule) -> Optional[models.Schedule]:
        with self.dbconn.session.begin() as session:
            schedule_orm = models.ScheduleDB(**schedule.model_dump(exclude={"tasks"}))
            session.add(schedule_orm)

            created_schedule = models.Schedule.model_validate(schedule_orm)

            return created_schedule

    @retry()
    def update_schedule(self, schedule: models.Schedule) -> None:
        with self.dbconn.session.begin() as session:
            (
                session.query(models.ScheduleDB)
                .filter(models.ScheduleDB.id == schedule.id)
                .update(schedule.model_dump(exclude={"tasks"}))
            )

    @retry()
    def update_schedule_enabled(self, schedule_id: str, enabled: bool) -> None:
        with self.dbconn.session.begin() as session:
            (session.query(models.ScheduleDB).filter(models.ScheduleDB.id == schedule_id).update({"enabled": enabled}))

    @retry()
    def delete_schedule(self, schedule_id: str) -> None:
        with self.dbconn.session.begin() as session:
            session.query(models.ScheduleDB).filter(models.ScheduleDB.id == schedule_id).delete()
