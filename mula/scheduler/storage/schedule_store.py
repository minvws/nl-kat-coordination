from sqlalchemy import exc, func

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
        schedule_id: str | None = None,
        schedule_hash: str | None = None,
        filters: FilterRequest | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[models.Schedule], int]:
        with self.dbconn.session.begin() as session:
            query = session.query(models.ScheduleDB)

            if schedule_id is not None:
                query = query.filter(models.ScheduleDB.id == schedule_id)

            if schedule_hash is not None:
                query = query.filter(models.ScheduleDB.hash == schedule_hash)

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
    def get_schedule(self, schedule_id: str) -> models.Schedule:
        with self.dbconn.session.begin() as session:
            schedule_orm = session.query(models.ScheduleDB).filter(models.ScheduleDB.id == schedule_id).one_or_none()

            if schedule_orm is None:
                return None

            return models.Schedule.model_validate(schedule_orm)

    def get_schedule_by_hash(self, schedule_hash: str) -> models.Schedule:
        with self.dbconn.session.begin() as session:
            schedule_orm = (
                session.query(models.ScheduleDB).filter(models.ScheduleDB.hash == schedule_hash).one_or_none()
            )

            if schedule_orm is None:
                return None

            return models.Schedule.model_validate(schedule_orm)

    @retry()
    def create_schedule(self, schedule: models.Schedule) -> models.Schedule:
        with self.dbconn.session.begin() as session:
            schedule_orm = models.ScheduleDB(**schedule.model_dump())
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
    def delete_schedule(self, schedule_id: str) -> None:
        with self.dbconn.session.begin() as session:
            session.query(models.ScheduleDB).filter(models.ScheduleDB.id == schedule_id).delete()
