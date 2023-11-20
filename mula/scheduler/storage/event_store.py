from datetime import datetime
from typing import Optional

from scheduler.models import EventDB, TaskStatus

from .storage import DBConn, retry


class EventStore:
    name: str = "event_store"

    def __init__(self, dbconn: DBConn) -> None:
        self.dbconn = dbconn

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
                .order_by(EventDB.datetime.asc())
            )

            result_start = query.first()
            if result_start is not None:
                start_time = result_start.datetime

            # Get task event end time when status is completed or failed
            query = (
                session.query(EventDB)
                .filter(EventDB.task_id == task_id)
                .filter(EventDB.type == "events.db")
                .filter(EventDB.context == "task")
                .filter(EventDB.event == "update")
                .filter(EventDB.data["status"].as_string() == TaskStatus.DISPATCHED.upper())
                .order_by(EventDB.datetime.desc())
            )

            result_end = query.first()
            if result_end is not None:
                end_time = result_end.datetime

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
                .order_by(EventDB.datetime.asc())
            )

            result_start = query.first()
            if result_start is not None:
                start_time = result_start.datetime

            # Get task event end time when status is completed or failed
            query = (
                session.query(EventDB)
                .filter(EventDB.task_id == task_id)
                .filter(EventDB.type == "events.db")
                .filter(EventDB.context == "task")
                .filter(EventDB.event == "update")
                .filter(EventDB.data["status"].as_string().in_([TaskStatus.COMPLETED.upper(), TaskStatus.FAILED.upper()]))
                .order_by(EventDB.datetime.desc())
            )

            result_end = query.first()
            if result_end is not None:
                end_time = result_end.datetime

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
                .order_by(EventDB.datetime.asc())
            )

            result_start = query.first()
            if result_start is not None:
                start_time = result_start.datetime

            # Get task event end time when status is completed or failed
            query = (
                session.query(EventDB)
                .filter(EventDB.task_id == task_id)
                .filter(EventDB.type == "events.db")
                .filter(EventDB.context == "task")
                .filter(EventDB.event == "update")
                .filter(EventDB.data["status"].as_string().in_([TaskStatus.COMPLETED.upper(), TaskStatus.FAILED.upper()]))
                .order_by(EventDB.datetime.desc())
            )

            result_end = query.first()
            if result_end is not None:
                end_time = result_end.datetime

        if start_time is not None and end_time is not None:
            return (end_time - start_time).total_seconds()

        return 0
