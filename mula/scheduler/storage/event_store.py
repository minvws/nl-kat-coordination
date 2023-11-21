from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import exc

from scheduler.models import Event, EventDB, TaskStatus

from .filters import FilterRequest, apply_filter
from .storage import DBConn, retry


class EventStore:
    name: str = "event_store"

    def __init__(self, dbconn: DBConn) -> None:
        self.dbconn = dbconn

    @retry()
    def get_events(
        self,
        task_id: Optional[str] = None,
        type: Optional[str] = None,
        context: Optional[str] = None,
        event: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        offset: int = 0,
        limit: int = 100,
        filters: Optional[FilterRequest] = None,
    ) -> Tuple[List[Event], int]:
        with self.dbconn.session.begin() as session:
            query = session.query(EventDB)

            if task_id is not None:
                query = query.filter(EventDB.task_id == task_id)

            if type is not None:
                query = query.filter(EventDB.type == type)

            if context is not None:
                query = query.filter(EventDB.context == context)

            if event is not None:
                query = query.filter(EventDB.event == event)

            if timestamp is not None:
                query = query.filter(EventDB.timestamp == timestamp)

            if filters is not None:
                query = apply_filter(EventDB, query, filters)

            try:
                count = query.count()
                events_orm = query.order_by(EventDB.timestamp.desc()).offset(offset).limit(limit).all()
            except exc.ProgrammingError as e:
                raise ValueError(f"Invalid filter: {e}") from e

            events = [Event.model_validate(event_orm) for event_orm in events_orm]

        return events, count

    @retry()
    def create_event(self, event: Event) -> None:
        with self.dbconn.session.begin() as session:
            event_orm = EventDB(**event.model_dump())
            session.add(event_orm)

            created_event = Event.model_validate(event_orm)

        return created_event

    @retry()
    def get_task_queued(self, task_id: str) -> float:
        """Get task queued (how long has task been on queue) time in seconds
        """
        start_time: Optional[datetime] = None
        end_time: Optional[datetime] = None

        with self.dbconn.session.begin() as session:
            query = (
                session.query(EventDB)
                .filter(EventDB.task_id == task_id)
                .filter(EventDB.type == "events.db")
                .filter(EventDB.context == "task")
                .filter(EventDB.event == "insert")
                .filter(EventDB.data["status"].as_string() == TaskStatus.QUEUED.upper())
                .order_by(EventDB.timestamp.asc())
            )

            result_start = query.first()
            if result_start is not None:
                start_time = result_start.timestamp

            # Get task event end time when status is completed or failed
            query = (
                session.query(EventDB)
                .filter(EventDB.task_id == task_id)
                .filter(EventDB.type == "events.db")
                .filter(EventDB.context == "task")
                .filter(EventDB.event == "update")
                .filter(EventDB.data["status"].as_string() == TaskStatus.DISPATCHED.upper())
                .order_by(EventDB.timestamp.desc())
            )

            result_end = query.first()
            if result_end is not None:
                end_time = result_end.timestamp

        if start_time is not None and end_time is not None:
            return (end_time - start_time).total_seconds()

        return 0

    @retry()
    def get_task_runtime(self, task_id: str) -> float:
        """Get task runtime in seconds
        """
        start_time: Optional[datetime] = None
        end_time: Optional[datetime] = None

        with self.dbconn.session.begin() as session:
            query = (
                session.query(EventDB)
                .filter(EventDB.task_id == task_id)
                .filter(EventDB.type == "events.db")
                .filter(EventDB.context == "task")
                .filter(EventDB.event == "update")
                .filter(EventDB.data["status"].as_string() == TaskStatus.DISPATCHED.upper())
                .order_by(EventDB.timestamp.asc())
            )

            result_start = query.first()
            if result_start is not None:
                start_time = result_start.timestamp

            # Get task event end time when status is completed or failed
            query = (
                session.query(EventDB)
                .filter(EventDB.task_id == task_id)
                .filter(EventDB.type == "events.db")
                .filter(EventDB.context == "task")
                .filter(EventDB.event == "update")
                .filter(EventDB.data["status"].as_string().in_([TaskStatus.COMPLETED.upper(), TaskStatus.FAILED.upper()]))
                .order_by(EventDB.timestamp.desc())
            )

            result_end = query.first()
            if result_end is not None:
                end_time = result_end.timestamp

        if start_time is not None and end_time is not None:
            return (end_time - start_time).total_seconds()

        return 0

    @retry()
    def get_task_duration(self, task_id: str) -> float:
        """Total duration of a task from start to finish in seconds
        """
        start_time: Optional[datetime] = None
        end_time: Optional[datetime] = None

        with self.dbconn.session.begin() as session:
            query = (
                session.query(EventDB)
                .filter(EventDB.task_id == task_id)
                .filter(EventDB.type == "events.db")
                .filter(EventDB.context == "task")
                .filter(EventDB.event == "insert")
                .filter(EventDB.data["status"].as_string() == TaskStatus.QUEUED.upper())
                .order_by(EventDB.timestamp.asc())
            )

            result_start = query.first()
            if result_start is not None:
                start_time = result_start.timestamp

            # Get task event end time when status is completed or failed
            query = (
                session.query(EventDB)
                .filter(EventDB.task_id == task_id)
                .filter(EventDB.type == "events.db")
                .filter(EventDB.context == "task")
                .filter(EventDB.event == "update")
                .filter(EventDB.data["status"].as_string().in_([TaskStatus.COMPLETED.upper(), TaskStatus.FAILED.upper()]))
                .order_by(EventDB.timestamp.desc())
            )

            result_end = query.first()
            if result_end is not None:
                end_time = result_end.timestamp

        if start_time is not None and end_time is not None:
            return (end_time - start_time).total_seconds()

        return 0
